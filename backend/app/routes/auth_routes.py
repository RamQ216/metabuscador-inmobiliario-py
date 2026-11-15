from flask import Blueprint, request, jsonify, session
from app.models import db, Usuario, Rol
from app.services.security import verificar_rate_limit, validar_email_formato, sanitizar_texto

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/api/v1/auth/login', methods=['POST'])
def login():
    """
    Autentica al usuario mediante email y contraseña (Requisito 8.2: Login de ingreso).
    Aplica Rate Limiting por IP contra fuerza bruta y emite sesión firmada HttpOnly.
    """
    if not verificar_rate_limit('auth_login', max_intentos=10, ventana_segundos=60):
        return jsonify({
            'status': 'error',
            'message': 'Demasiados intentos de inicio de sesión. Aguarde un minuto.'
        }), 429

    data = request.get_json() or {}
    email = sanitizar_texto(data.get('email'), 150).lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'status': 'error', 'message': 'Debe ingresar correo y contraseña'}), 400

    usuario = Usuario.query.filter(db.func.lower(Usuario.email) == email).first()

    if not usuario or not usuario.check_password(password):
        return jsonify({'status': 'error', 'message': 'Credenciales inválidas'}), 401

    if not usuario.activo:
        return jsonify({'status': 'error', 'message': 'La cuenta de usuario está desactivada'}), 403

    # Registra datos en la sesión firmada del servidor con expiración controlada
    session.permanent = True
    session['user_id'] = usuario.id
    session['rol_nombre'] = usuario.rol.nombre if usuario.rol else 'Cliente'

    return jsonify({
        'status': 'success',
        'message': f'Bienvenido/a {usuario.nombre}',
        'user': usuario.to_dict()
    }), 200


@auth_bp.route('/api/v1/auth/logout', methods=['POST'])
def logout():
    """Cierra la sesión activa del usuario actual limpiando la cookie."""
    session.clear()
    return jsonify({'status': 'success', 'message': 'Sesión cerrada correctamente'}), 200


@auth_bp.route('/api/v1/auth/me', methods=['GET'])
def current_user():
    """Verifica si existe una sesión activa y devuelve los datos del usuario logueado."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'status': 'unauthenticated', 'user': None}), 200

    usuario = Usuario.query.get(user_id)
    if not usuario or not usuario.activo:
        session.clear()
        return jsonify({'status': 'unauthenticated', 'user': None}), 200

    return jsonify({'status': 'authenticated', 'user': usuario.to_dict()}), 200


@auth_bp.route('/api/v1/auth/register', methods=['POST'])
def register():
    """Permite registrar un nuevo usuario con rol Cliente validando formato y longitud."""
    if not verificar_rate_limit('auth_register', max_intentos=5, ventana_segundos=60):
        return jsonify({'status': 'error', 'message': 'Límite de registros excedido. Intente más tarde.'}), 429

    data = request.get_json() or {}
    nombre = sanitizar_texto(data.get('nombre'), 100)
    apellido = sanitizar_texto(data.get('apellido'), 100)
    email = sanitizar_texto(data.get('email'), 150).lower()
    password = data.get('password') or ''
    telefono = sanitizar_texto(data.get('telefono'), 30)

    if not all([nombre, apellido, email, password]):
        return jsonify({'status': 'error', 'message': 'Todos los campos obligatorios deben completarse'}), 400

    if not validar_email_formato(email):
        return jsonify({'status': 'error', 'message': 'El formato del correo electrónico no es válido'}), 400

    if len(password) < 6:
        return jsonify({'status': 'error', 'message': 'La contraseña debe tener al menos 6 caracteres'}), 400

    if Usuario.query.filter(db.func.lower(Usuario.email) == email).first():
        return jsonify({'status': 'error', 'message': 'El correo electrónico ya está registrado'}), 409

    rol_cliente = Rol.query.filter_by(nombre='Cliente').first() or Rol.query.first()

    nuevo_usuario = Usuario(
        rol_id=rol_cliente.id,
        nombre=nombre,
        apellido=apellido,
        email=email,
        telefono=telefono,
        activo=True
    )
    nuevo_usuario.set_password(password)

    db.session.add(nuevo_usuario)
    db.session.commit()

    session.permanent = True
    session['user_id'] = nuevo_usuario.id
    session['rol_nombre'] = rol_cliente.nombre

    return jsonify({
        'status': 'success',
        'message': 'Cuenta creada con éxito',
        'user': nuevo_usuario.to_dict()
    }), 201
