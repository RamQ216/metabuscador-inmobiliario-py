import os
import secrets
from datetime import timedelta

# Obtiene la ruta absoluta del directorio base del backend
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))


class Config:
    """
    Configuración central y políticas de seguridad de la aplicación Flask.
    Soporta PostgreSQL (Supabase) mediante DATABASE_URL y SQLite local como respaldo.
    """
    # Clave criptográfica de sesión; en producción usa variable de entorno o genera token seguro
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)

    # Endurecimiento de cookies de sesión contra robo por XSS y ataques CSRF (OWASP A05)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)

    # Lista blanca de orígenes permitidos para peticiones CORS autenticadas
    ALLOWED_ORIGINS = [
        o.strip() for o in os.environ.get(
            'ALLOWED_ORIGINS',
            'http://127.0.0.1:5000,http://localhost:5000,http://127.0.0.1:5500,http://localhost:5500'
        ).split(',') if o.strip()
    ]

    # Obtiene la URI de la base de datos o usa archivo local SQLite si no está configurada
    _db_url = os.environ.get('DATABASE_URL', f"sqlite:///{os.path.join(BASE_DIR, 'inmuebles_py.db')}")

    # Corrige el prefijo 'postgres://' antiguo que algunos proveedores en la nube devuelven
    if _db_url.startswith('postgres://'):
        _db_url = _db_url.replace('postgres://', 'postgresql://', 1)

    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Tasa de cambio referencial por defecto (USD -> PYG) y tiempo de vida de caché (6 horas)
    DEFAULT_USD_TO_PYG = 7800.0
    CURRENCY_CACHE_TTL_SECONDS = 6 * 3600
