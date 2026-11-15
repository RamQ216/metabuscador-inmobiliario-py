from datetime import datetime, date
from flask import Blueprint, request, jsonify, session
from sqlalchemy.orm import joinedload, selectinload
from app.models import db, SolicitudVisita, SolicitudDetalle, Publicacion, Inmueble
from app.services.security import login_required, sanitizar_texto, parsear_int_positivo

movement_bp = Blueprint('movements', __name__)


@movement_bp.route('/api/v1/movements/visits', methods=['GET'])
def list_visit_requests():
    """
    Lista los movimientos de Solicitud de Visita Comparada (Requisito 8.1)
    precargando relaciones para evitar consultas N+1.
    Si el usuario es Cliente autenticado ve únicamente sus propias solicitudes.
    """
    user_id = session.get('user_id')
    rol_nombre = session.get('rol_nombre', 'Cliente')

    query = SolicitudVisita.query.options(
        joinedload(SolicitudVisita.usuario),
        joinedload(SolicitudVisita.inmueble).joinedload(Inmueble.barrio),
        selectinload(SolicitudVisita.detalles).joinedload(SolicitudDetalle.publicacion).joinedload(Publicacion.agencia)
    ).order_by(SolicitudVisita.id.desc())

    # Si hay un usuario Cliente logueado, restringe la vista a sus propios movimientos (Prevención IDOR)
    if user_id and rol_nombre != 'Administrador':
        query = query.filter_by(usuario_id=user_id)

    solicitudes = [s.to_dict() for s in query.all()]
    return jsonify({
        'status': 'success',
        'count': len(solicitudes),
        'data': solicitudes
    }), 200


@movement_bp.route('/api/v1/movements/visits', methods=['POST'])
@login_required
def create_visit_request():
    """
    Registra un nuevo Movimiento Transaccional con Cabecera (solicitudes_visita)
    y Detalle (solicitud_detalles) exigiendo sesión activa y tomando el usuario
    exclusivamente desde la sesión del servidor (Prevención de suplantación IDOR).
    """
    data = request.get_json() or {}
    # Identidad tomada estrictamente de la sesión firmada en el servidor
    user_id = session['user_id']

    inmueble_id = parsear_int_positivo(data.get('inmueble_id'), 'inmueble_id', permitir_cero=False)
    publicacion_ids = data.get('publicacion_ids', [])
    fecha_str = sanitizar_texto(data.get('fecha_visita_propuesta'), 20)
    horario = sanitizar_texto(data.get('horario_preferido') or 'Mañana (09:00 - 12:00)', 50)
    observaciones = sanitizar_texto(data.get('observaciones'), 500)

    if not isinstance(publicacion_ids, list) or len(publicacion_ids) == 0:
        return jsonify({'status': 'error', 'message': 'Debe seleccionar al menos una oferta de agencia'}), 400

    # Verifica que el inmueble exista
    inmueble = Inmueble.query.get_or_404(inmueble_id)

    try:
        fecha_visita = datetime.strptime(fecha_str, '%Y-%m-%d').date() if fecha_str else date.today()
    except ValueError:
        return jsonify({'status': 'error', 'message': 'Formato de fecha inválido (use YYYY-MM-DD)'}), 400

    # 1. Crea la Cabecera del Movimiento
    nueva_solicitud = SolicitudVisita(
        usuario_id=user_id,
        inmueble_id=inmueble.id,
        fecha_visita_propuesta=fecha_visita,
        horario_preferido=horario,
        estado='PENDIENTE',
        observaciones=observaciones
    )
    db.session.add(nueva_solicitud)
    db.session.flush()

    # 2. Crea los registros de Detalle del Movimiento congelando precios y expensas en PYG
    detalles_creados = 0
    for pub_id in set(publicacion_ids):
        pub = Publicacion.query.get(parsear_int_positivo(pub_id, 'publicacion_id', permitir_cero=False))
        if pub and pub.inmueble_id == inmueble.id:
            detalle = SolicitudDetalle(
                solicitud_id=nueva_solicitud.id,
                publicacion_id=pub.id,
                precio_congelado_pyg=float(pub.precio_pyg),
                expensas_congeladas_pyg=float(pub.expensas_pyg or 0),
                comentario_agencia=f"Agencia {pub.agencia.nombre if pub.agencia else ''} seleccionada para comparación"
            )
            db.session.add(detalle)
            detalles_creados += 1

    if detalles_creados == 0:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Las publicaciones seleccionadas no corresponden al inmueble'}), 400

    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Solicitud de visita comparada registrada correctamente',
        'data': nueva_solicitud.to_dict()
    }), 201


@movement_bp.route('/api/v1/movements/visits/<int:solicitud_id>/status', methods=['PUT'])
@login_required
def update_visit_status(solicitud_id):
    """
    Actualiza el estado del movimiento validando que el usuario sea propietario de la
    solicitud o tenga rol Administrador (Prevención IDOR).
    """
    solicitud = SolicitudVisita.query.get_or_404(solicitud_id)
    user_id = session.get('user_id')
    rol_nombre = session.get('rol_nombre', 'Cliente')

    if rol_nombre != 'Administrador' and solicitud.usuario_id != user_id:
        return jsonify({'status': 'error', 'message': 'No tiene permiso para modificar solicitudes de otro usuario'}), 403

    data = request.get_json() or {}
    nuevo_estado = sanitizar_texto(data.get('estado'), 20).upper()

    estados_validos = ('PENDIENTE', 'CONFIRMADA', 'REALIZADA', 'CANCELADA')
    if nuevo_estado not in estados_validos:
        return jsonify({'status': 'error', 'message': 'Estado no válido'}), 400

    # Un cliente regular solo puede cancelar su propia solicitud; el Administrador puede confirmar o dar por realizada
    if rol_nombre != 'Administrador' and nuevo_estado not in ('CANCELADA', 'PENDIENTE'):
        return jsonify({'status': 'error', 'message': 'Solo un Administrador puede confirmar o cerrar solicitudes'}), 403

    solicitud.estado = nuevo_estado
    if 'observaciones' in data and data['observaciones'] is not None:
        solicitud.observaciones = sanitizar_texto(data['observaciones'], 500)

    db.session.commit()
    return jsonify({
        'status': 'success',
        'message': f'Estado de la solicitud actualizado a {nuevo_estado}',
        'data': solicitud.to_dict()
    }), 200


@movement_bp.route('/api/v1/movements/visits/<int:solicitud_id>', methods=['DELETE'])
@login_required
def delete_visit_request(solicitud_id):
    """
    Elimina una solicitud de visita validando propiedad del registro o rol Administrador.
    """
    solicitud = SolicitudVisita.query.get_or_404(solicitud_id)
    user_id = session.get('user_id')
    rol_nombre = session.get('rol_nombre', 'Cliente')

    if rol_nombre != 'Administrador' and solicitud.usuario_id != user_id:
        return jsonify({'status': 'error', 'message': 'No tiene permiso para eliminar solicitudes de otro usuario'}), 403

    db.session.delete(solicitud)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Solicitud eliminada correctamente'}), 200
