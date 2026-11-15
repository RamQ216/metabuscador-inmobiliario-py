from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload
from app.models import db, Agencia, Ciudad, Barrio, TipoInmueble, Usuario, Rol
from app.services.deduplication import procesar_y_guardar_publicacion
from app.services.security import (
    admin_required,
    verificar_rate_limit,
    validar_email_formato,
    sanitizar_texto,
    parsear_int_positivo,
    parsear_float_positivo
)
from scrapers.run_scrapers import ejecutar_pipeline_scraping

maintenance_bp = Blueprint('maintenance', __name__)


# =============================================================================
# 1. MANTENIMIENTO DE AGENCIAS INMOBILIARIAS (CRUD Completo protegido por Rol)
# =============================================================================
@maintenance_bp.route('/api/v1/maintenance/agencies', methods=['GET'])
@admin_required
def list_agencies():
    """Devuelve todas las agencias registradas para la tabla de mantenimiento."""
    agencias = [a.to_dict() for a in Agencia.query.order_by(Agencia.id).all()]
    return jsonify({'status': 'success', 'data': agencias}), 200


@maintenance_bp.route('/api/v1/maintenance/agencies', methods=['POST'])
@admin_required
def create_agency():
    """Crea una nueva agencia inmobiliaria validando datos requeridos."""
    data = request.get_json() or {}
    nombre = sanitizar_texto(data.get('nombre'), 100)
    sitio_web = sanitizar_texto(data.get('sitio_web'), 255)

    if not nombre or not sitio_web:
        return jsonify({'status': 'error', 'message': 'Nombre y sitio web son obligatorios'}), 400

    if Agencia.query.filter(db.func.lower(Agencia.nombre) == nombre.lower()).first():
        return jsonify({'status': 'error', 'message': 'Ya existe una agencia con ese nombre'}), 409

    nueva = Agencia(
        nombre=nombre,
        sitio_web=sitio_web,
        logo_url=sanitizar_texto(data.get('logo_url'), 500),
        telefono_contacto=sanitizar_texto(data.get('telefono_contacto'), 50),
        activo=bool(data.get('activo', True))
    )
    db.session.add(nueva)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Agencia creada', 'data': nueva.to_dict()}), 201


@maintenance_bp.route('/api/v1/maintenance/agencies/<int:agency_id>', methods=['PUT'])
@admin_required
def update_agency(agency_id):
    """Actualiza los datos de una agencia inmobiliaria existente."""
    agencia = Agencia.query.get_or_404(agency_id)
    data = request.get_json() or {}

    if 'nombre' in data and data['nombre']:
        agencia.nombre = sanitizar_texto(data['nombre'], 100)
    if 'sitio_web' in data and data['sitio_web']:
        agencia.sitio_web = sanitizar_texto(data['sitio_web'], 255)
    if 'logo_url' in data:
        agencia.logo_url = sanitizar_texto(data['logo_url'], 500)
    if 'telefono_contacto' in data:
        agencia.telefono_contacto = sanitizar_texto(data['telefono_contacto'], 50)
    if 'activo' in data:
        agencia.activo = bool(data['activo'])

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Agencia actualizada', 'data': agencia.to_dict()}), 200


@maintenance_bp.route('/api/v1/maintenance/agencies/<int:agency_id>', methods=['DELETE'])
@admin_required
def delete_agency(agency_id):
    """Elimina una agencia inmobiliaria si no posee publicaciones asociadas."""
    agencia = Agencia.query.get_or_404(agency_id)
    if agencia.publicaciones:
        return jsonify({'status': 'error', 'message': 'No se puede eliminar una agencia con publicaciones activas'}), 400
    db.session.delete(agencia)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Agencia eliminada'}), 200


# =============================================================================
# 2. MANTENIMIENTO DE CIUDADES Y BARRIOS (CRUD Completo protegido por Rol)
# =============================================================================
@maintenance_bp.route('/api/v1/maintenance/cities', methods=['GET', 'POST'])
@admin_required
def manage_cities():
    """Lista todas las ciudades o registra una nueva ciudad en el catálogo maestro."""
    if request.method == 'GET':
        return jsonify({'status': 'success', 'data': [c.to_dict() for c in Ciudad.query.order_by(Ciudad.id).all()]}), 200

    data = request.get_json() or {}
    nombre = sanitizar_texto(data.get('nombre'), 100)
    departamento = sanitizar_texto(data.get('departamento') or 'Central', 100)
    if not nombre:
        return jsonify({'status': 'error', 'message': 'El nombre de la ciudad es obligatorio'}), 400

    if Ciudad.query.filter(db.func.lower(Ciudad.nombre) == nombre.lower()).first():
        return jsonify({'status': 'error', 'message': 'La ciudad ya existe en el catálogo'}), 409

    ciudad = Ciudad(nombre=nombre, departamento=departamento)
    db.session.add(ciudad)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Ciudad creada', 'data': ciudad.to_dict()}), 201


@maintenance_bp.route('/api/v1/maintenance/cities/<int:ciudad_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_or_delete_city(ciudad_id):
    """Actualiza o elimina una ciudad si no tiene barrios dependientes."""
    ciudad = Ciudad.query.get_or_404(ciudad_id)
    if request.method == 'DELETE':
        if ciudad.barrios:
            return jsonify({'status': 'error', 'message': 'No se puede eliminar una ciudad con barrios asociados'}), 400
        db.session.delete(ciudad)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Ciudad eliminada'}), 200

    data = request.get_json() or {}
    if 'nombre' in data and data['nombre']:
        ciudad.nombre = sanitizar_texto(data['nombre'], 100)
    if 'departamento' in data and data['departamento']:
        ciudad.departamento = sanitizar_texto(data['departamento'], 100)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Ciudad actualizada', 'data': ciudad.to_dict()}), 200


@maintenance_bp.route('/api/v1/maintenance/neighborhoods', methods=['GET', 'POST'])
@admin_required
def manage_neighborhoods():
    """Lista los barrios con sus coordenadas centroides o crea un nuevo barrio validando rango GPS."""
    if request.method == 'GET':
        barrios = [
            b.to_dict() for b in Barrio.query.options(joinedload(Barrio.ciudad)).order_by(Barrio.id).all()
        ]
        return jsonify({'status': 'success', 'data': barrios}), 200

    data = request.get_json() or {}
    ciudad_id = parsear_int_positivo(data.get('ciudad_id'), 'ciudad_id', permitir_cero=False)
    nombre = sanitizar_texto(data.get('nombre'), 100)

    try:
        lat = float(data.get('lat_centroide', -25.2867))
        lon = float(data.get('lon_centroide', -57.6470))
    except (TypeError, ValueError):
        return jsonify({'status': 'error', 'message': 'Coordenadas GPS inválidas'}), 400

    if not (-28.0 <= lat <= -19.0 and -63.0 <= lon <= -54.0):
        return jsonify({'status': 'error', 'message': 'Las coordenadas deben corresponder al territorio de Paraguay'}), 400

    if not nombre:
        return jsonify({'status': 'error', 'message': 'El nombre del barrio es obligatorio'}), 400

    barrio = Barrio(
        ciudad_id=ciudad_id,
        nombre=nombre,
        lat_centroide=lat,
        lon_centroide=lon
    )
    db.session.add(barrio)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Barrio registrado', 'data': barrio.to_dict()}), 201


@maintenance_bp.route('/api/v1/maintenance/neighborhoods/<int:barrio_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_or_delete_neighborhood(barrio_id):
    """Modifica o elimina un barrio del catálogo geográfico."""
    barrio = Barrio.query.get_or_404(barrio_id)

    if request.method == 'DELETE':
        if barrio.inmuebles:
            return jsonify({'status': 'error', 'message': 'No se puede eliminar un barrio con inmuebles asociados'}), 400
        db.session.delete(barrio)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Barrio eliminado'}), 200

    data = request.get_json() or {}
    if 'nombre' in data and data['nombre']:
        barrio.nombre = sanitizar_texto(data['nombre'], 100)
    if 'ciudad_id' in data and data['ciudad_id']:
        barrio.ciudad_id = parsear_int_positivo(data['ciudad_id'], 'ciudad_id', permitir_cero=False)
    if 'lat_centroide' in data:
        barrio.lat_centroide = float(data['lat_centroide'])
    if 'lon_centroide' in data:
        barrio.lon_centroide = float(data['lon_centroide'])

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Barrio actualizado', 'data': barrio.to_dict()}), 200


# =============================================================================
# 3. MANTENIMIENTO DE TIPOS DE INMUEBLE (CRUD Completo protegido por Rol)
# =============================================================================
@maintenance_bp.route('/api/v1/maintenance/property-types', methods=['GET', 'POST'])
@admin_required
def manage_property_types():
    """Lista o crea nuevos tipos de inmueble (Departamento, Casa, Dúplex, etc.)."""
    if request.method == 'GET':
        tipos = [t.to_dict() for t in TipoInmueble.query.order_by(TipoInmueble.id).all()]
        return jsonify({'status': 'success', 'data': tipos}), 200

    data = request.get_json() or {}
    nombre = sanitizar_texto(data.get('nombre'), 50)
    descripcion = sanitizar_texto(data.get('descripcion'), 200)
    if not nombre:
        return jsonify({'status': 'error', 'message': 'El nombre del tipo es obligatorio'}), 400

    nuevo = TipoInmueble(nombre=nombre, descripcion=descripcion)
    db.session.add(nuevo)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Tipo de inmueble creado', 'data': nuevo.to_dict()}), 201


@maintenance_bp.route('/api/v1/maintenance/property-types/<int:tipo_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_or_delete_property_type(tipo_id):
    """Actualiza o elimina un tipo de inmueble."""
    tipo = TipoInmueble.query.get_or_404(tipo_id)
    if request.method == 'DELETE':
        if tipo.inmuebles:
            return jsonify({'status': 'error', 'message': 'No se puede eliminar un tipo con inmuebles asociados'}), 400
        db.session.delete(tipo)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Tipo eliminado'}), 200

    data = request.get_json() or {}
    if 'nombre' in data and data['nombre']:
        tipo.nombre = sanitizar_texto(data['nombre'], 50)
    if 'descripcion' in data:
        tipo.descripcion = sanitizar_texto(data['descripcion'], 200)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Tipo actualizado', 'data': tipo.to_dict()}), 200


# =============================================================================
# 4. MANTENIMIENTO DE USUARIOS Y ROLES (CRUD Completo protegido por Rol)
# =============================================================================
@maintenance_bp.route('/api/v1/maintenance/users', methods=['GET', 'POST'])
@admin_required
def manage_users():
    """Lista todos los usuarios del sistema o da de alta uno nuevo desde administración."""
    if request.method == 'GET':
        usuarios = [
            u.to_dict() for u in Usuario.query.options(joinedload(Usuario.rol)).order_by(Usuario.id).all()
        ]
        roles = [r.to_dict() for r in Rol.query.order_by(Rol.id).all()]
        return jsonify({'status': 'success', 'data': usuarios, 'roles': roles}), 200

    data = request.get_json() or {}
    email = sanitizar_texto(data.get('email'), 150).lower()
    if not validar_email_formato(email):
        return jsonify({'status': 'error', 'message': 'Formato de correo electrónico inválido'}), 400

    if Usuario.query.filter(db.func.lower(Usuario.email) == email).first():
        return jsonify({'status': 'error', 'message': 'El email ya existe'}), 409

    password = data.get('password') or ''
    if len(password) < 6:
        return jsonify({'status': 'error', 'message': 'La contraseña debe tener al menos 6 caracteres'}), 400

    usuario = Usuario(
        rol_id=parsear_int_positivo(data.get('rol_id', 2), 'rol_id', permitir_cero=False),
        nombre=sanitizar_texto(data.get('nombre'), 100),
        apellido=sanitizar_texto(data.get('apellido'), 100),
        email=email,
        telefono=sanitizar_texto(data.get('telefono'), 30),
        activo=bool(data.get('activo', True))
    )
    usuario.set_password(password)
    db.session.add(usuario)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Usuario creado', 'data': usuario.to_dict()}), 201


@maintenance_bp.route('/api/v1/maintenance/users/<int:user_id>', methods=['PUT', 'DELETE'])
@admin_required
def update_or_delete_user(user_id):
    """Modifica el rol/estado de un usuario o lo elimina si no tiene historial transaccional."""
    usuario = Usuario.query.get_or_404(user_id)
    if request.method == 'DELETE':
        if usuario.solicitudes:
            return jsonify({'status': 'error', 'message': 'El usuario posee solicitudes registradas; desactívelo en su lugar'}), 400
        db.session.delete(usuario)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Usuario eliminado'}), 200

    data = request.get_json() or {}
    if 'nombre' in data and data['nombre']:
        usuario.nombre = sanitizar_texto(data['nombre'], 100)
    if 'apellido' in data and data['apellido']:
        usuario.apellido = sanitizar_texto(data['apellido'], 100)
    if 'rol_id' in data and data['rol_id']:
        usuario.rol_id = parsear_int_positivo(data['rol_id'], 'rol_id', permitir_cero=False)
    if 'telefono' in data:
        usuario.telefono = sanitizar_texto(data['telefono'], 30)
    if 'activo' in data:
        usuario.activo = bool(data['activo'])
    if data.get('password'):
        if len(data['password']) < 6:
            return jsonify({'status': 'error', 'message': 'La contraseña nueva debe tener mínimo 6 caracteres'}), 400
        usuario.set_password(data['password'])

    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Usuario actualizado', 'data': usuario.to_dict()}), 200


# =============================================================================
# 5. INGESTA DE PUBLICACIONES Y DISPARADOR DE SCRAPING (Protegido por Rol y Rate-Limit)
# =============================================================================
@maintenance_bp.route('/api/v1/maintenance/listings', methods=['POST'])
@admin_required
def create_listing_with_deduplication():
    """
    Permite cargar un aviso de agencia validando precios y superficies positivas,
    ejecutando el motor de puntuación (Scoring) para deduplicación automática.
    """
    data = request.get_json() or {}
    required = ['agencia_id', 'url_externa', 'titulo_original', 'precio_original']
    if not all(data.get(k) for k in required):
        return jsonify({'status': 'error', 'message': 'Faltan campos requeridos de la publicación'}), 400

    datos_limpios = {
        'agencia_id': parsear_int_positivo(data.get('agencia_id'), 'agencia_id', permitir_cero=False),
        'url_externa': sanitizar_texto(data.get('url_externa'), 500),
        'titulo_original': sanitizar_texto(data.get('titulo_original'), 255),
        'descripcion': sanitizar_texto(data.get('descripcion', ''), 1000),
        'barrio_nombre': sanitizar_texto(data.get('barrio_nombre', 'Villa Morra'), 100),
        'tipo_inmueble': sanitizar_texto(data.get('tipo_inmueble', 'Departamento'), 50),
        'tipo_operacion': sanitizar_texto(data.get('tipo_operacion', 'alquiler'), 20).lower(),
        'moneda_original': sanitizar_texto(data.get('moneda_original', 'PYG'), 3).upper(),
        'precio_original': parsear_float_positivo(data.get('precio_original'), 'precio_original', permitir_cero=False),
        'expensas_original': parsear_float_positivo(data.get('expensas_original', 0), 'expensas_original', permitir_cero=True),
        'superficie_m2': parsear_float_positivo(data.get('superficie_m2', 60), 'superficie_m2', permitir_cero=False),
        'dormitorios': parsear_int_positivo(data.get('dormitorios', 1), 'dormitorios', permitir_cero=False),
        'banos': parsear_int_positivo(data.get('banos', 1), 'banos', permitir_cero=False)
    }

    pub, agrupado = procesar_y_guardar_publicacion(datos_limpios)
    return jsonify({
        'status': 'success',
        'message': 'Publicación vinculada a propiedad existente (Deduplicada)' if agrupado else 'Nueva propiedad física creada',
        'fue_agrupado': agrupado,
        'data': pub.to_dict()
    }), 201


@maintenance_bp.route('/api/v1/maintenance/run-scraper', methods=['POST'])
@admin_required
def trigger_scraper():
    """Ejecuta bajo demanda el pipeline de scraping con protección de frecuencia."""
    if not verificar_rate_limit('run_scraper', max_intentos=3, ventana_segundos=60):
        return jsonify({'status': 'error', 'message': 'El scraper ya fue ejecutado recientemente. Aguarde un minuto.'}), 429

    resumen = ejecutar_pipeline_scraping()
    return jsonify({
        'status': 'success',
        'message': f"Extracción finalizada: {resumen['total_extraidos']} avisos procesados, {resumen['duplicados_cruzados']} duplicados agrupados.",
        'data': resumen
    }), 200
