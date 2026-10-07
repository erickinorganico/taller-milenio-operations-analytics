"""Gmail REST + Windows user-scoped encrypted credential storage. No external packages."""
import base64
import ctypes
import json
import os
from datetime import datetime, timezone
from email.message import EmailMessage
from email.utils import parseaddr
from email import policy
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from django.conf import settings

SCOPES = ['https://www.googleapis.com/auth/gmail.send', 'https://www.googleapis.com/auth/gmail.readonly']
TOKEN_URL = 'https://oauth2.googleapis.com/token'
API = 'https://gmail.googleapis.com/gmail/v1/users/me/'


def protect(data, decrypt=False):
    if os.name != 'nt':
        raise RuntimeError('Este almacén de credenciales requiere Windows DPAPI.')
    from ctypes import wintypes
    class Blob(ctypes.Structure):
        _fields_ = [('size', wintypes.DWORD), ('data', ctypes.POINTER(ctypes.c_ubyte))]
    buffer = ctypes.create_string_buffer(data)
    incoming = Blob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_ubyte)))
    outgoing = Blob()
    api = ctypes.windll.crypt32.CryptUnprotectData if decrypt else ctypes.windll.crypt32.CryptProtectData
    api.argtypes = [ctypes.POINTER(Blob), ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(Blob)]
    api.restype = wintypes.BOOL
    if not api(ctypes.byref(incoming), None, None, None, None, 1, ctypes.byref(outgoing)):
        raise ctypes.WinError()
    try:
        return ctypes.string_at(outgoing.data, outgoing.size)
    finally:
        ctypes.windll.kernel32.LocalFree.argtypes = [ctypes.c_void_p]
        ctypes.windll.kernel32.LocalFree(outgoing.data)


def credential_path():
    return Path(settings.DATA_DIR) / '.gmail.dpapi'


def save_credentials(values):
    path = credential_path()
    temporary = path.with_suffix('.pending')
    temporary.write_bytes(protect(json.dumps(values).encode()))
    temporary.replace(path)


def token_request(values):
    request = Request(TOKEN_URL, data=urlencode(values).encode(), method='POST')
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def b64decode(value):
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(); self.text = []; self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'): self.hidden += 1
        if tag in ('p', 'br', 'div'): self.text.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style'): self.hidden = max(0, self.hidden - 1)
    def handle_data(self, data):
        if not self.hidden: self.text.append(data)


def parse_message(data):
    payload = data.get('payload', {})
    headers = {h['name'].lower(): h['value'] for h in payload.get('headers', [])}
    plain, rich = [], []
    def visit(part):
        if part.get('filename'): return
        content = part.get('body', {}).get('data', '')
        if content and part.get('mimeType') in ('text/plain', 'text/html'):
            decoded = b64decode(content).decode('utf-8', errors='replace')
            (plain if part['mimeType'] == 'text/plain' else rich).append(decoded)
        for child in part.get('parts', []): visit(child)
    visit(payload)
    body = '\n'.join(plain)
    if not body and rich:
        parser = PlainHTML(); parser.feed('\n'.join(rich)); body = ''.join(parser.text)
    return {'id': data['id'], 'thread_id': data['threadId'], 'sender': parseaddr(headers.get('from', ''))[1].lower(),
            'subject': headers.get('subject', ''), 'headers': headers, 'body': body[:50000],
            'rfc_id': headers.get('message-id', ''), 'sent': 'SENT' in data.get('labelIds', []),
            'draft': 'DRAFT' in data.get('labelIds', []), 'spam': 'SPAM' in data.get('labelIds', []),
            'date': datetime.fromtimestamp(int(data['internalDate']) / 1000, timezone.utc)}


class GmailClient:
    def __init__(self, access_token=None):
        if access_token is None:
            values = json.loads(protect(credential_path().read_bytes(), decrypt=True))
            refreshed = token_request({'client_id': values['client_id'], 'client_secret': values['client_secret'],
                                       'refresh_token': values['refresh_token'], 'grant_type': 'refresh_token'})
            access_token = refreshed['access_token']
        self.access_token = access_token

    def request(self, path, data=None):
        request = Request(API + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={'Authorization': 'Bearer ' + self.access_token, 'Content-Type': 'application/json'})
        with urlopen(request, timeout=30) as response:
            return json.load(response)

    def thread(self, thread_id):
        if not thread_id.isalnum(): raise ValueError('Invalid Gmail thread id')
        return [parse_message(m) for m in self.request('threads/' + thread_id + '?format=full').get('messages', [])]

    def discover(self, address, since):
        # Also recognize human replies that start a new thread, and messages sent manually.
        query = f'{{from:{address} to:{address}}} after:{int(since.timestamp())}'
        queries = [query, f'after:{int(since.timestamp())} {{from:mailer-daemon from:postmaster}} "{address}"']
        matched = {}
        for query in queries:
            page = self.request('messages?' + urlencode({'q': query, 'maxResults': 100, 'includeSpamTrash': 'true'}))
            if page.get('nextPageToken'):
                raise RuntimeError('Demasiados mensajes nuevos: revisar el buzón antes de enviar')
            matched.update({m['id']: m for m in page.get('messages', [])})
        result = []
        for m in matched.values():
            item = parse_message(self.request('messages/' + m['id'] + '?format=full'))
            if item['date'] >= since:
                result.append(item)
        return sorted(result, key=lambda x: x['date'])

    def find_sent(self, rfc_id):
        results = self.request('messages?' + urlencode({'q': 'in:sent rfc822msgid:' + rfc_id.strip('<>'), 'maxResults': 2})).get('messages', [])
        if len(results) > 1: raise RuntimeError('Identificador repetido en Gmail')
        return results[0] if results else None

    def send(self, message, sender):
        mime = EmailMessage(policy=policy.SMTP)
        mime['From'] = 'Equipo Milenio <' + sender + '>'
        mime['To'] = message.recipient
        mime['Subject'] = message.subject
        mime['Message-ID'] = message.rfc_id
        if message.reply_to_id:
            mime['In-Reply-To'] = message.reply_to_id
            mime['References'] = message.reply_to_id
        if message.kind == 'auto':
            mime['Auto-Submitted'] = 'auto-replied'
            mime['X-Auto-Response-Suppress'] = 'All'
        mime.set_content(message.body)
        if message.html: mime.add_alternative(message.html, subtype='html')
        payload = {'raw': base64.urlsafe_b64encode(mime.as_bytes()).decode()}
        if message.thread_id: payload['threadId'] = message.thread_id
        return self.request('messages/send', payload)
