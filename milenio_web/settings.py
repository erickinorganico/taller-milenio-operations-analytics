"""Single-workshop settings. Private database and credentials never enter artifacts."""
import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MILENIO_MODE = os.environ.get("MILENIO_MODE", "live")
if MILENIO_MODE not in {"live", "demo", "test"}:
    raise RuntimeError("MILENIO_MODE must be live, demo or test")


def default_data_root():
    """Use the user's local app-data area, not the extractable project folder."""
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    return Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local" / "share")


DATA_DIR = Path(os.environ.get("MILENIO_DATA_DIR") or
                default_data_root() / "Milenio" / "operational" / MILENIO_MODE).resolve()
DATA_DIR.mkdir(parents=True, exist_ok=True)
secret_file = DATA_DIR / ".secret_key"
if not secret_file.exists():
    try:
        with secret_file.open("x", encoding="utf-8") as handle:
            handle.write(secrets.token_urlsafe(64))
    except FileExistsError:
        pass
SECRET_KEY = os.environ.get("MILENIO_SECRET_KEY") or secret_file.read_text(encoding="utf-8").strip()
DEBUG = False
ALLOWED_HOSTS = [s.strip() for s in os.environ.get("MILENIO_ALLOWED_HOSTS", "127.0.0.1,localhost,[::1]").split(",") if s.strip()]
INSTALLED_APPS = ["django.contrib.auth", "django.contrib.contenttypes", "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles", "workshop"]
MIDDLEWARE = ["django.middleware.security.SecurityMiddleware", "django.contrib.sessions.middleware.SessionMiddleware", "django.middleware.common.CommonMiddleware", "django.middleware.csrf.CsrfViewMiddleware", "django.contrib.auth.middleware.AuthenticationMiddleware", "django.contrib.messages.middleware.MessageMiddleware", "django.middleware.clickjacking.XFrameOptionsMiddleware", "workshop.access.AccessMiddleware"]
ROOT_URLCONF = "milenio_web.urls"
TEMPLATES = [{"BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": True, "OPTIONS": {"context_processors": ["django.template.context_processors.request", "django.contrib.auth.context_processors.auth", "django.contrib.messages.context_processors.messages", "workshop.access.navigation"]}}]
WSGI_APPLICATION = "milenio_web.wsgi.application"
DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": DATA_DIR / "workshop.sqlite3", "OPTIONS": {"timeout": 30, "transaction_mode": "IMMEDIATE"}}}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
AUTH_PASSWORD_VALIDATORS = [{"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"}, {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}}, {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"}, {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"}]
LANGUAGE_CODE = "es-mx"
TIME_ZONE = os.environ.get("MILENIO_TIME_ZONE", "America/Tijuana")
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = DATA_DIR / "static"
MEDIA_ROOT = DATA_DIR / "media"
MEDIA_URL = "/evidence/"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/login/"
SESSION_COOKIE_NAME = f"milenio_{MILENIO_MODE}_session"
CSRF_COOKIE_NAME = f"milenio_{MILENIO_MODE}_csrf"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
CSRF_COOKIE_SAMESITE = "Strict"
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
if os.environ.get("MILENIO_HTTPS") == "1":
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
MILENIO_CODEX_ENABLED = os.environ.get("MILENIO_CODEX_ENABLED") == "1"
