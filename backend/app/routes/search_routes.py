from flask import Blueprint, request, jsonify
from sqlalchemy.orm import joinedload, selectinload
from app.models import db, Inmueble, Publicacion, Ciudad, Barrio, TipoInmueble, Agencia

search_bp = Blueprint('search', __name__)


@search_bp.route('/api/v1/health', methods=['GET'])
def health_check():
    """
    Endpoint ligero de Keep-Alive para que un cron o servicio de monitoreo haga ping
    cada 14 minutos y evite el arranque en frío (Cold Start) en Render.
    """
    return jsonify({'status': 'ok', 'service': 'inmuebles-py-api'}), 200


@search_bp.route('/api/v1/catalogs', methods=['GET'])
def get_catalogs():
    """
    Devuelve los catálogos maestros en 3FN (Ciudades, Barrios, Tipos de Inmueble y Agencias)
    optimizando la carga de Ciudad en Barrio mediante joinedload.
    """
    ciudades = [c.to_dict() for c in Ciudad.query.order_by(Ciudad.id).all()]
    barrios = [
        b.to_dict() for b in Barrio.query.options(joinedload(Barrio.ciudad)).order_by(Barrio.nombre).all()
    ]
    tipos = [t.to_dict() for t in TipoInmueble.query.order_by(TipoInmueble.id).all()]
    agencias = [a.to_dict() for a in Agencia.query.filter_by(activo=True).order_by(Agencia.id).all()]

    return jsonify({
        'status': 'success',
        'ciudades': ciudades,
        'barrios': barrios,
        'tipos_inmueble': tipos,
        'agencias': agencias
    }), 200


@search_bp.route('/api/v1/properties/search', methods=['GET'])
def search_properties():
    """
    Busca inmuebles físicos resolviendo filtros en SQL y precargando relaciones con
    joinedload/selectinload para eliminar el problema de consultas N+1.
    Soporta paginación (page, per_page).
    """
    ciudad_id = request.args.get('ciudad_id', type=int)
    barrio_id = request.args.get('barrio_id', type=int)
    tipo_inmueble_id = request.args.get('tipo_inmueble_id', type=int)
    operacion = request.args.get('operacion', default='').strip().lower()
    dormitorios_min = request.args.get('dormitorios', type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    solo_duplicados = request.args.get('solo_duplicados', default='false').lower() == 'true'
    q = (request.args.get('q') or '').strip()

    page = max(request.args.get('page', default=1, type=int), 1)
    per_page = min(max(request.args.get('per_page', default=50, type=int), 1), 100)

    # Construye consulta precargando relaciones (Barrio -> Ciudad, TipoInmueble y Publicaciones -> Agencia)
    query = Inmueble.query.join(Barrio).join(Publicacion).options(
        joinedload(Inmueble.barrio).joinedload(Barrio.ciudad),
        joinedload(Inmueble.tipo_inmueble),
        selectinload(Inmueble.publicaciones).joinedload(Publicacion.agencia)
    ).filter(Publicacion.activo.is_(True))

    if ciudad_id:
        query = query.filter(Barrio.ciudad_id == ciudad_id)
    if barrio_id:
        query = query.filter(Inmueble.barrio_id == barrio_id)
    if tipo_inmueble_id:
        query = query.filter(Inmueble.tipo_inmueble_id == tipo_inmueble_id)
    if dormitorios_min:
        query = query.filter(Inmueble.dormitorios >= dormitorios_min)
    if operacion in ('alquiler', 'venta'):
        query = query.filter(Publicacion.tipo_operacion == operacion)
    if min_price is not None:
        query = query.filter(Publicacion.precio_pyg >= min_price)
    if max_price is not None:
        query = query.filter(Publicacion.precio_pyg <= max_price)
    if q:
        query = query.filter(
            db.or_(
                Inmueble.titulo_canonico.ilike(f'%{q}%'),
                Inmueble.nombre_edificio.ilike(f'%{q}%'),
                Barrio.nombre.ilike(f'%{q}%')
            )
        )

    # Evita filas repetidas por el JOIN con publicaciones y ordena de más reciente a más antiguo
    inmuebles = query.distinct().order_by(Inmueble.id.desc()).all()
    resultados = []

    for inm in inmuebles:
        pubs_activas = [p for p in inm.publicaciones if p.activo]
        if operacion in ('alquiler', 'venta'):
            pubs_activas = [p for p in pubs_activas if p.tipo_operacion == operacion]
        if min_price is not None:
            pubs_activas = [p for p in pubs_activas if float(p.precio_pyg) >= min_price]
        if max_price is not None:
            pubs_activas = [p for p in pubs_activas if float(p.precio_pyg) <= max_price]

        if not pubs_activas:
            continue
        if solo_duplicados and len(pubs_activas) < 2:
            continue

        resultados.append(inm.to_summary_dict(active_listings=pubs_activas))

    # Aplica paginación controlada sobre los resultados agrupados
    total_items = len(resultados)
    inicio = (page - 1) * per_page
    fin = inicio + per_page
    pagina_datos = resultados[inicio:fin]

    return jsonify({
        'status': 'success',
        'count': len(pagina_datos),
        'total': total_items,
        'page': page,
        'per_page': per_page,
        'data': pagina_datos
    }), 200


@search_bp.route('/api/v1/properties/<int:inmueble_id>/compare', methods=['GET'])
def compare_property(inmueble_id):
    """
    Devuelve la ficha completa de un inmueble físico y todas sus publicaciones
    precargadas en una sola consulta optimizada.
    """
    inmueble = Inmueble.query.options(
        joinedload(Inmueble.barrio).joinedload(Barrio.ciudad),
        joinedload(Inmueble.tipo_inmueble),
        selectinload(Inmueble.publicaciones).joinedload(Publicacion.agencia)
    ).get_or_404(inmueble_id)

    pubs_activas = sorted(
        [p for p in inmueble.publicaciones if p.activo],
        key=lambda x: float(x.precio_pyg)
    )

    resumen = inmueble.to_summary_dict(active_listings=pubs_activas)

    if resumen['superficie_m2'] > 0 and resumen['precio_min_pyg'] > 0:
        resumen['precio_m2_min_pyg'] = round(resumen['precio_min_pyg'] / resumen['superficie_m2'], 0)
    else:
        resumen['precio_m2_min_pyg'] = 0

    return jsonify({
        'status': 'success',
        'data': resumen
    }), 200


@search_bp.route('/api/v1/analytics/price-per-m2', methods=['GET'])
def analytics_price_per_m2():
    """
    Calcula directamente mediante agregación SQL el valor promedio por metro cuadrado
    (Gs./m2) agrupado por barrio, evitando cargar entidades en memoria.
    """
    operacion = request.args.get('operacion', default='alquiler').lower()

    filas = db.session.query(
        Barrio.id,
        Barrio.nombre,
        Ciudad.nombre.label('ciudad_nombre'),
        db.func.avg(Publicacion.precio_pyg / Inmueble.superficie_m2).label('promedio_m2'),
        db.func.count(Publicacion.id).label('muestras')
    ).join(Ciudad, Barrio.ciudad_id == Ciudad.id)\
     .join(Inmueble, Inmueble.barrio_id == Barrio.id)\
     .join(Publicacion, Publicacion.inmueble_id == Inmueble.id)\
     .filter(
         Publicacion.activo.is_(True),
         Publicacion.tipo_operacion == operacion,
         Inmueble.superficie_m2 > 0
     ).group_by(Barrio.id, Barrio.nombre, Ciudad.nombre).all()

    estadisticas = [{
        'barrio_id': f.id,
        'barrio': f.nombre,
        'ciudad': f.ciudad_nombre,
        'operacion': operacion,
        'promedio_gs_m2': round(float(f.promedio_m2 or 0), 0),
        'muestras': int(f.muestras)
    } for f in filas]

    return jsonify({
        'status': 'success',
        'data': estadisticas
    }), 200
