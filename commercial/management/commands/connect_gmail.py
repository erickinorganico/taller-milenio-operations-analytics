"""Interactive installed-app OAuth. Credentials are protected by the current Windows user."""
import base64
import hashlib
import json
import secrets
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlsplit
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from commercial.gmail import GmailClient, SCOPES, token_request, save_credentials
from commercial.models import Mailbox


class Command(BaseCommand):
    help = 'Conectar Gmail mediante OAuth de aplicación de escritorio; no envía correos.'

    def add_arguments(self, parser):
        parser.add_argument('--client', required=True, help='JSON OAuth de aplicación de escritorio descargado de Google Cloud')
        parser.add_argument('--owner', required=True, help='Usuario de Gerencia existente en Milenio')

    def handle(self, *args, **options):
        owner = get_user_model().objects.filter(username=options['owner'], is_active=True, is_superuser=True).first()
        if not owner: raise CommandError('Primero crea Gerencia desde /setup/ y utiliza ese usuario.')
        box, _ = Mailbox.objects.get_or_create(pk=1)
        if box.enabled: raise CommandError('Pausa el correo en el panel antes de reconectar Gmail.')
        try:
            installed = json.loads(Path(options['client']).read_text(encoding='utf-8-sig'))['installed']
            client_id, client_secret = installed['client_id'], installed['client_secret']
        except (OSError, KeyError, ValueError):
            raise CommandError('Selecciona el JSON de un cliente OAuth de tipo Aplicación de escritorio.')
        verifier = secrets.token_urlsafe(64)
        challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        state = secrets.token_urlsafe(32)
        received = {}
        class Callback(BaseHTTPRequestHandler):
            def log_message(self, *args): pass  # OAuth codes must never be logged.
            def do_GET(self):
                parsed = urlsplit(self.path)
                query = parse_qs(parsed.query)
                valid = parsed.path == '/callback' and secrets.compare_digest(query.get('state', [''])[0], state)
                if valid:
                    received.update({k: v[0] for k, v in query.items()})
                self.send_response(200 if valid else 400)
                self.send_header('Content-Type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(('Autorización recibida. Puedes cerrar esta pestaña.' if valid else 'Solicitud no válida.').encode())
        with HTTPServer(('127.0.0.1', 0), Callback) as server:
            redirect = f'http://127.0.0.1:{server.server_port}/callback'
            url = 'https://accounts.google.com/o/oauth2/v2/auth?' + urlencode({
                'client_id': client_id, 'redirect_uri': redirect, 'response_type': 'code', 'scope': ' '.join(SCOPES),
                'state': state, 'code_challenge': challenge, 'code_challenge_method': 'S256',
                'access_type': 'offline', 'prompt': 'consent'})
            self.stdout.write('Abriendo Google para elegir y autorizar el Gmail comercial; espera máxima: 5 minutos.')
            webbrowser.open(url)
            server.timeout = 1
            deadline = time.monotonic() + 300
            while not received and time.monotonic() < deadline:
                server.handle_request()
        if not received.get('code'): raise CommandError('No se completó la autorización. No se conectó Gmail.')
        try:
            tokens = token_request({'code': received['code'], 'client_id': client_id, 'client_secret': client_secret,
                'redirect_uri': redirect, 'grant_type': 'authorization_code', 'code_verifier': verifier})
            if not tokens.get('refresh_token'): raise ValueError('Missing refresh token')
            if not set(SCOPES).issubset(set(tokens.get('scope', '').split())): raise ValueError('Missing scopes')
            email = GmailClient(tokens['access_token']).request('profile')['emailAddress'].lower()
            if box.email and box.email != email:
                raise CommandError('La instalación pertenece a otro Gmail. Usa el mismo buzón para conservar la trazabilidad.')
            save_credentials({'client_id': client_id, 'client_secret': client_secret, 'refresh_token': tokens['refresh_token']})
        except CommandError: raise
        except Exception:
            raise CommandError('No se pudo conectar o guardar Gmail. No se imprimen credenciales; revisa permisos y vuelve a autorizar.')
        box.email, box.owner, box.connected, box.enabled = email, owner, True, False
        box.last_error = ''; box.save()
        self.stdout.write('Gmail conectado. Revisa la cola y activa el flujo desde Comercial → Correo.')
