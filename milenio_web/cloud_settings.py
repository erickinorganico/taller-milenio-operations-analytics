"""Production settings for one persistent workshop behind its private Unix socket."""
import ipaddress
import os
import re
import secrets
import tempfile
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured


def cloud_configuration():
    os.umask(0o077)
    host = os.environ.get("MILENIO_CLOUD_HOST", "")
    labels = host.split(".")
    if (len(labels) < 2 or len(host) > 253 or
            any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels)):
        raise ImproperlyConfigured("MILENIO_CLOUD_HOST requiere un único nombre DNS en minúsculas.")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise ImproperlyConfigured("Usa el nombre DNS certificado, no una dirección IP.")
    directory = Path(os.environ.get("MILENIO_DATA_DIR", ""))
    if not directory.is_absolute() or not directory.is_dir() or directory.is_symlink():
        raise ImproperlyConfigured("Monta un directorio persistente absoluto en MILENIO_DATA_DIR.")
    if (os.environ.get("MILENIO_MODE") != "live" or os.environ.get("MILENIO_DEPLOYMENT_CONFIG")
            or os.environ.get("MILENIO_SECRET_KEY")):
        raise ImproperlyConfigured("La nube usa MILENIO_MODE=live y su propio archivo de clave persistente.")
    from .deployment import config_path
    if config_path().is_file():
        raise ImproperlyConfigured("La configuración local de Windows no pertenece al servicio de nube.")
    # Atomically publish the complete key before independent workers import settings.
    secret = directory / ".secret_key"
    if not secret.exists():
        with tempfile.NamedTemporaryFile(dir=directory, delete=False) as new:
            new.write(secrets.token_urlsafe(64).encode("ascii"))
            temporary = Path(new.name)
        try:
            if os.name == "nt":
                # Windows rename is exclusive and supports isolated configuration QA.
                temporary.rename(secret)
            else:
                os.link(temporary, secret)
        except FileExistsError:
            pass
        finally:
            temporary.unlink(missing_ok=True)
    if (secret.is_symlink() or not secret.is_file() or
            (os.name == "posix" and secret.stat().st_mode & 0o077) or
            len(secret.read_text(encoding="ascii").strip()) < 50):
        raise ImproperlyConfigured("La clave persistente debe ser privada y contener al menos 50 caracteres.")
    return host


CLOUD_HOST = cloud_configuration()
from .settings import *  # noqa: E402,F403

MILENIO_CLOUD = True
MILENIO_CODEX_ENABLED = False
ALLOWED_HOSTS = [CLOUD_HOST]
CSRF_TRUSTED_ORIGINS = ["https://" + CLOUD_HOST]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
# HTTPS policy applies to the configured workshop hostname. No promises about
# other subdomains or ownership of a browser preload registration.
SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]
ROOT_URLCONF = "milenio_web.cloud_urls"
FILE_UPLOAD_PERMISSIONS = 0o600
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o700
