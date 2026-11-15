import time
import re
from functools import wraps
from flask import session, request, jsonify
from app.models import Usuario

# Almacén en memoria para control de límite de peticiones (Rate Limiting por IP/ruta)
_rate_limit_store = {}


def verificar_rate_limit(clave_accion, max_intentos=10, ventana_segundos=60):
    """
    Verifica si una dirección IP ha superado el número máximo de peticiones permitidas
    en una ventana de tiempo para prevenir ataques de fuerza bruta o denegación de servicio.
    """
    ip_cliente = request.remote_addr or '127.0.0.1'
    identificador = f"{clave_accion}:{ip_cliente}"
    ahora = time.time()

    historial = _rate_limit_store.get(identificador, [])
    # Conserva únicamente las marcas de tiempo dentro de la ventana activa
    historial = [t for t in historial if ahora - t < ventana_segundos]

    if len(historial) >= max_intentos:
        _rate_limit_store[identificador] = historial
        return False

    historial.append(ahora)
    _rate_limit_store[identificador] = historial
    return True


def login_required(f):
    """
    Decorador de seguridad que exige una sesión autenticada válida en el servidor
    antes de ejecutar cualquier operación protegida (Prevención OWASP A01).
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Acceso denegado: Debe iniciar sesión para realizar esta operación'
            }), 401

        usuario = Usuario.query.get(user_id)
        if not usuario or not usuario.activo:
            session.clear()
            return jsonify({
                'status': 'error',
                'message': 'Sesión inválida o usuario desactivado'
            }), 401

        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorador de seguridad que exige que el usuario autenticado posea el rol
    'Administrador' para acceder a los Mantenimientos (ABM) o disparar el Scraper.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Acceso restringido: Inicie sesión como Administrador'
            }), 401

        usuario = Usuario.query.get(user_id)
        if not usuario or not usuario.activo or not usuario.rol or usuario.rol.nombre != 'Administrador':
            return jsonify({
                'status': 'error',
                'message': 'Permisos insuficientes: Esta acción requiere rol de Administrador'
            }), 403

        return f(*args, **kwargs)
    return decorated_function


def validar_email_formato(email):
    """Comprueba mediante expresión regular que el correo tenga un formato estándar válido."""
    if not email or len(email) > 150:
        return False
    patron = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    return bool(re.match(patron, email))


def sanitizar_texto(valor, max_len=255):
    """Limpia espacios excedentes y recorta la longitud máxima permitida de un texto."""
    if valor is None:
        return ''
    texto = str(valor).strip()
    return texto[:max_len]


def parsear_float_positivo(valor, nombre_campo='valor', permitir_cero=True):
    """Convierte y valida que un número decimal sea válido y no negativo."""
    try:
        num = float(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El campo '{nombre_campo}' debe ser un número válido")

    if permitir_cero and num < 0:
        raise ValueError(f"El campo '{nombre_campo}' no puede ser negativo")
    if not permitir_cero and num <= 0:
        raise ValueError(f"El campo '{nombre_campo}' debe ser mayor a cero")
    return num


def parsear_int_positivo(valor, nombre_campo='valor', permitir_cero=True):
    """Convierte y valida que un número entero sea válido y no negativo."""
    try:
        num = int(valor)
    except (TypeError, ValueError):
        raise ValueError(f"El campo '{nombre_campo}' debe ser un número entero válido")

    if permitir_cero and num < 0:
        raise ValueError(f"El campo '{nombre_campo}' no puede ser negativo")
    if not permitir_cero and num <= 0:
        raise ValueError(f"El campo '{nombre_campo}' debe ser mayor a cero")
    return num
