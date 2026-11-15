import re
import unicodedata
from datetime import datetime
from app.models import db, Inmueble, Publicacion, Barrio, TipoInmueble
from app.services.currency import normalizar_a_guaranies

# Puntaje mínimo (de 0 a 100) para considerar que dos avisos son la misma propiedad física
UMBRAL_SIMILITUD = 75


def limpiar_texto(texto):
    """Elimina tildes, caracteres especiales y convierte a minúsculas para comparar textos."""
    if not texto:
        return ''
    texto_nfd = unicodedata.normalize('NFD', str(texto))
    sin_tildes = ''.join(c for c in texto_nfd if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9\s]', ' ', sin_tildes.lower()).strip()


def detectar_nombre_edificio(titulo, descripcion=''):
    """
    Extrae el nombre del edificio o condominio en caso de departamentos
    (Ej: 'Edificio Feel', 'Torre Miranda', 'Live Boggiani').
    """
    texto_completo = f"{titulo} {descripcion or ''}"
    patrones = [
        r'(edificio\s+[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+(?:\s+[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+)?)',
        r'(torre[s]?\s+[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+)',
        r'(condominio\s+[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ]+)'
    ]
    for patron in patrones:
        match = re.search(patron, texto_completo, re.IGNORECASE)
        if match:
            return match.group(1).strip().title()
    return None


def mapear_barrio_catalogo(nombre_barrio_crudo):
    """
    Normaliza el nombre del barrio extraído por el scraper contra el Catálogo Maestro
    de la tabla 'barrios' para evitar duplicidades como 'Ycua Sati' vs 'Ycuá Satí'.
    """
    limpio = limpiar_texto(nombre_barrio_crudo)
    todos_los_barrios = Barrio.query.all()

    # Diccionario de sinónimos frecuentes en portales paraguayos
    sinonimos = {
        'shopping del sol': 'ycua sati',
        'ykua sati': 'ycua sati',
        'carmelitas': 'las lomas',
        'conmebol': 'zona conmebol',
        'aeropuerto': 'zona conmebol',
        'yacht': 'canal 13'
    }

    for clave, destino in sinonimos.items():
        if clave in limpio:
            limpio = destino
            break

    for barrio in todos_los_barrios:
        nombre_catalogo = limpiar_texto(barrio.nombre)
        if nombre_catalogo in limpio or limpio in nombre_catalogo:
            return barrio

    # Si no encuentra coincidencia, asigna el primer barrio por defecto (Villa Morra)
    return todos_los_barrios[0] if todos_los_barrios else None


def calcular_puntaje_coincidencia(inmueble_existente, datos_nuevos, precio_nuevo_pyg):
    """
    Calcula el puntaje acumulado (0 a 100 pts) entre un inmueble existente en el mismo
    barrio y un nuevo aviso entrante para decidir si son la misma propiedad física.
    """
    puntaje = 0

    # 1. Coincidencia de Barrio y Tipo de Inmueble (+35 pts base: 20 barrio + 15 tipo)
    if inmueble_existente.barrio_id != datos_nuevos['barrio_id']:
        return 0
    if inmueble_existente.tipo_inmueble_id != datos_nuevos['tipo_inmueble_id']:
        return 0
    puntaje += 35

    # 2. Evaluación de Dormitorios (+20 exacto | +10 con diferencia de 1 por área de servicio)
    dif_dorm = abs(inmueble_existente.dormitorios - datos_nuevos.get('dormitorios', 1))
    if dif_dorm == 0:
        puntaje += 20
    elif dif_dorm == 1:
        puntaje += 10

    # 3. Evaluación de Superficie m2 (+25 si dif <= 5% | +15 si dif <= 15%)
    sup_existente = float(inmueble_existente.superficie_m2 or 0)
    sup_nueva = float(datos_nuevos.get('superficie_m2') or 0)
    if sup_existente > 0 and sup_nueva > 0:
        diferencia_pct = abs(sup_existente - sup_nueva) / max(sup_existente, sup_nueva)
        if diferencia_pct <= 0.05:
            puntaje += 25
        elif diferencia_pct <= 0.15:
            puntaje += 15

    # 4. Evaluación de Precio Normalizado en PYG (+15 si dif <= 12%)
    precios_actuales = [float(p.precio_pyg) for p in inmueble_existente.publicaciones if p.activo]
    if precios_actuales and precio_nuevo_pyg > 0:
        precio_prom = sum(precios_actuales) / len(precios_actuales)
        dif_precio_pct = abs(precio_prom - precio_nuevo_pyg) / max(precio_prom, precio_nuevo_pyg)
        if dif_precio_pct <= 0.12:
            puntaje += 15

    # 5. Coincidencia de Nombre de Edificio o Palabras Clave (+30 pts extra)
    edif_existente = limpiar_texto(inmueble_existente.nombre_edificio)
    edif_nuevo = limpiar_texto(datos_nuevos.get('nombre_edificio'))
    if edif_existente and edif_nuevo and (edif_existente in edif_nuevo or edif_nuevo in edif_existente):
        puntaje += 30

    return min(puntaje, 100)


def procesar_y_guardar_publicacion(datos_aviso):
    """
    Recibe los datos crudos de un aviso extraído por el scraper, normaliza su precio a PYG,
    ejecuta el algoritmo de deduplicación y guarda/actualiza el registro en la BD.
    """
    precio_pyg = normalizar_a_guaranies(datos_aviso['precio_original'], datos_aviso.get('moneda_original', 'PYG'))
    expensas_pyg = normalizar_a_guaranies(datos_aviso.get('expensas_original', 0), 'PYG')

    # Verifica si la URL exacta ya fue registrada previamente para solo actualizarla
    pub_existente = Publicacion.query.filter_by(url_externa=datos_aviso['url_externa']).first()
    if pub_existente:
        pub_existente.precio_original = datos_aviso['precio_original']
        pub_existente.precio_pyg = precio_pyg
        pub_existente.expensas_pyg = expensas_pyg
        pub_existente.activo = True
        pub_existente.ultima_extraccion = datetime.utcnow()
        db.session.commit()
        return pub_existente, False

    # Normaliza barrio y tipo de inmueble contra los catálogos en 3FN
    barrio = mapear_barrio_catalogo(datos_aviso.get('barrio_nombre', 'Villa Morra'))
    tipo = TipoInmueble.query.filter(
        TipoInmueble.nombre.ilike(f"%{datos_aviso.get('tipo_inmueble', 'Departamento')}%")
    ).first() or TipoInmueble.query.first()

    nombre_edificio = datos_aviso.get('nombre_edificio') or detectar_nombre_edificio(
        datos_aviso['titulo_original'], datos_aviso.get('descripcion', '')
    )

    datos_normalizados = {
        'barrio_id': barrio.id,
        'tipo_inmueble_id': tipo.id,
        'dormitorios': int(datos_aviso.get('dormitorios', 1)),
        'banos': int(datos_aviso.get('banos', 1)),
        'superficie_m2': float(datos_aviso.get('superficie_m2', 60)),
        'nombre_edificio': nombre_edificio
    }

    # Busca candidatos en el mismo barrio y tipo para evaluar puntaje de cruce
    candidatos = Inmueble.query.filter_by(
        barrio_id=barrio.id,
        tipo_inmueble_id=tipo.id
    ).all()

    mejor_candidato = None
    mejor_puntaje = 0

    for candidato in candidatos:
        score = calcular_puntaje_coincidencia(candidato, datos_normalizados, precio_pyg)
        if score > mejor_puntaje:
            mejor_puntaje = score
            mejor_candidato = candidato

    # Si supera el umbral de 75 puntos, se vincula a la propiedad física existente
    if mejor_candidato and mejor_puntaje >= UMBRAL_SIMILITUD:
        inmueble_destino = mejor_candidato
    else:
        # Si no supera el umbral, se crea una nueva entidad física de Inmueble
        inmueble_destino = Inmueble(
            tipo_inmueble_id=tipo.id,
            barrio_id=barrio.id,
            titulo_canonico=datos_aviso['titulo_original'],
            nombre_edificio=nombre_edificio,
            dormitorios=datos_normalizados['dormitorios'],
            banos=datos_normalizados['banos'],
            estacionamientos=int(datos_aviso.get('estacionamientos', 1)),
            superficie_m2=datos_normalizados['superficie_m2'],
            latitud=datos_aviso.get('latitud', barrio.lat_centroide),
            longitud=datos_aviso.get('longitud', barrio.lon_centroide)
        )
        db.session.add(inmueble_destino)
        db.session.flush()

    # Crea la publicación vinculada al inmueble físico
    nueva_pub = Publicacion(
        inmueble_id=inmueble_destino.id,
        agencia_id=datos_aviso['agencia_id'],
        url_externa=datos_aviso['url_externa'],
        titulo_original=datos_aviso['titulo_original'],
        descripcion=datos_aviso.get('descripcion', ''),
        tipo_operacion=datos_aviso.get('tipo_operacion', 'alquiler'),
        moneda_original=datos_aviso.get('moneda_original', 'PYG'),
        precio_original=datos_aviso['precio_original'],
        precio_pyg=precio_pyg,
        expensas_pyg=expensas_pyg,
        superficie_reportada_m2=datos_normalizados['superficie_m2'],
        imagen_url=datos_aviso.get('imagen_url'),
        activo=True
    )
    db.session.add(nueva_pub)
    db.session.commit()
    return nueva_pub, mejor_puntaje >= UMBRAL_SIMILITUD


def desactivar_publicaciones_caidas(agencia_id, urls_vigentes):
    """
    Desactiva automáticamente (activo = False) las publicaciones de una agencia que ya
    no aparecieron en el último barrido o devolvieron 404 (Ciclo de vida del dato).
    """
    if not urls_vigentes:
        return 0

    publicaciones_activas = Publicacion.query.filter_by(agencia_id=agencia_id, activo=True).all()
    desactivadas = 0

    for pub in publicaciones_activas:
        if pub.url_externa not in urls_vigentes:
            pub.activo = False
            desactivadas += 1

    db.session.commit()
    return desactivadas
