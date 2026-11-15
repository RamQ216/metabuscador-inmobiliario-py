from datetime import date, timedelta
from app.models import (
    db, Rol, Usuario, Ciudad, Barrio, TipoInmueble,
    Agencia, Inmueble, Publicacion, SolicitudVisita, SolicitudDetalle
)


def inicializar_datos_semilla():
    """
    Verifica si la base de datos está vacía al arrancar la aplicación y, de ser así,
    inserta automáticamente los catálogos en 3FN, usuarios de prueba con hash seguro,
    propiedades comparadas en Guaraníes y el movimiento de ejemplo.
    """
    if Rol.query.first() is not None:
        # Si la base fue cargada desde SQL externo, asegura que toda contraseña tenga hash criptográfico
        usuarios_existentes = Usuario.query.all()
        actualizado = False
        for u in usuarios_existentes:
            if u.password_hash and not (u.password_hash.startswith('scrypt:') or u.password_hash.startswith('pbkdf2:')):
                u.set_password(u.password_hash)
                actualizado = True
        if actualizado:
            db.session.commit()
        return

    # 1. Roles del sistema
    rol_admin = Rol(id=1, nombre='Administrador', descripcion='Acceso total a mantenimientos, scrapers y movimientos')
    rol_cliente = Rol(id=2, nombre='Cliente', descripcion='Acceso al metabuscador, comparador y solicitudes de visita')
    db.session.add_all([rol_admin, rol_cliente])
    db.session.flush()

    # 2. Usuarios iniciales (Login - Requisito 8.2)
    u_admin = Usuario(
        id=1, rol_id=1, nombre='Carlos', apellido='Administrador',
        email='admin@inmueblespy.com', telefono='0981-100200', activo=True
    )
    u_admin.set_password('admin123')

    u_cliente = Usuario(
        id=2, rol_id=2, nombre='María', apellido='González',
        email='maria@gmail.com', telefono='0971-555444', activo=True
    )
    u_cliente.set_password('cliente123')
    db.session.add_all([u_admin, u_cliente])

    # 3. Ciudades de cobertura (Asunción y Gran Asunción)
    ciudades = [
        Ciudad(id=1, nombre='Asunción', departamento='Capital'),
        Ciudad(id=2, nombre='Luque', departamento='Central'),
        Ciudad(id=3, nombre='San Lorenzo', departamento='Central'),
        Ciudad(id=4, nombre='Fernando de la Mora', departamento='Central'),
        Ciudad(id=5, nombre='Lambaré', departamento='Central'),
        Ciudad(id=6, nombre='Mariano Roque Alonso', departamento='Central')
    ]
    db.session.add_all(ciudades)
    db.session.flush()

    # 4. Catálogo Maestro de Barrios con coordenadas centroides reales
    barrios = [
        Barrio(id=1, ciudad_id=1, nombre='Villa Morra', lat_centroide=-25.2947, lon_centroide=-57.5806),
        Barrio(id=2, ciudad_id=1, nombre='Ycuá Satí', lat_centroide=-25.2878, lon_centroide=-57.5644),
        Barrio(id=3, ciudad_id=1, nombre='Las Lomas (Carmelitas)', lat_centroide=-25.2789, lon_centroide=-57.5692),
        Barrio(id=4, ciudad_id=1, nombre='Mburucuyá', lat_centroide=-25.2725, lon_centroide=-57.5583),
        Barrio(id=5, ciudad_id=1, nombre='Recoleta', lat_centroide=-25.2981, lon_centroide=-57.5919),
        Barrio(id=6, ciudad_id=1, nombre='Las Mercedes', lat_centroide=-25.2842, lon_centroide=-57.6114),
        Barrio(id=7, ciudad_id=2, nombre='Cuarto Barrio', lat_centroide=-25.2667, lon_centroide=-57.4925),
        Barrio(id=8, ciudad_id=2, nombre='Zona Conmebol / Aeropuerto', lat_centroide=-25.2581, lon_centroide=-57.5236),
        Barrio(id=9, ciudad_id=4, nombre='Zona Norte', lat_centroide=-25.3133, lon_centroide=-57.5514),
        Barrio(id=10, ciudad_id=5, nombre='Canal 13 / Valle Apu\'a', lat_centroide=-25.3411, lon_centroide=-57.6186)
    ]
    db.session.add_all(barrios)

    # 5. Tipos de Inmueble (Departamentos, Casas y Dúplex)
    tipos = [
        TipoInmueble(id=1, nombre='Departamento', descripcion='Unidad en edificio de altura con amenities'),
        TipoInmueble(id=2, nombre='Casa', descripcion='Vivienda unifamiliar independiente con patio'),
        TipoInmueble(id=3, nombre='Dúplex', descripcion='Vivienda de dos plantas pareada')
    ]
    db.session.add_all(tipos)

    # 6. Agencias Inmobiliarias (RE/MAX Paraguay e InfoCasas Paraguay)
    agencias = [
        Agencia(
            id=1, nombre='RE/MAX Paraguay', sitio_web='https://www.remax.com.py',
            logo_url='https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/ReMax_logo.svg/320px-ReMax_logo.svg.png',
            telefono_contacto='021-600700', activo=True
        ),
        Agencia(
            id=2, nombre='InfoCasas Paraguay', sitio_web='https://www.infocasas.com.py',
            logo_url='https://cdn2.infocasas.com.uy/web/5b4f7c2685386_infocasas-logo.png',
            telefono_contacto='021-300400', activo=True
        )
    ]
    db.session.add_all(agencias)
    db.session.flush()

    # 7. Inmuebles Físicos Deduplicados
    inmuebles = [
        Inmueble(
            id=1, tipo_inmueble_id=1, barrio_id=1,
            titulo_canonico='Departamento de 2 Dormitorios en Edificio Feel Asunción',
            nombre_edificio='Edificio Feel', dormitorios=2, banos=2, estacionamientos=1,
            superficie_m2=88.0, latitud=-25.2951, longitud=-57.5798
        ),
        Inmueble(
            id=2, tipo_inmueble_id=1, barrio_id=2,
            titulo_canonico='Departamento de 1 Dormitorio en Torre Miranda - Zona Shopping del Sol',
            nombre_edificio='Torre Miranda', dormitorios=1, banos=1, estacionamientos=1,
            superficie_m2=56.0, latitud=-25.2869, longitud=-57.5639
        ),
        Inmueble(
            id=3, tipo_inmueble_id=2, barrio_id=4,
            titulo_canonico='Residencia Familiar con Piscina en Barrio Mburucuyá',
            nombre_edificio=None, dormitorios=3, banos=3, estacionamientos=2,
            superficie_m2=240.0, latitud=-25.2731, longitud=-57.5579
        ),
        Inmueble(
            id=4, tipo_inmueble_id=3, barrio_id=8,
            titulo_canonico='Dúplex Moderno a Estrenar en Zona Conmebol - Luque',
            nombre_edificio=None, dormitorios=3, banos=3, estacionamientos=2,
            superficie_m2=165.0, latitud=-25.2589, longitud=-57.5228
        ),
        Inmueble(
            id=5, tipo_inmueble_id=1, barrio_id=6,
            titulo_canonico='Departamento Amplio en Las Mercedes sobre Padre Cardozo',
            nombre_edificio='Edificio Las Mercedes Plaza', dormitorios=2, banos=2, estacionamientos=1,
            superficie_m2=95.0, latitud=-25.2845, longitud=-57.6109
        ),
        Inmueble(
            id=6, tipo_inmueble_id=2, barrio_id=10,
            titulo_canonico='Casa Quinta Residencial en Lambaré Zona Yacht',
            nombre_edificio=None, dormitorios=4, banos=4, estacionamientos=3,
            superficie_m2=350.0, latitud=-25.3420, longitud=-57.6192
        )
    ]
    db.session.add_all(inmuebles)
    db.session.flush()

    # 8. Publicaciones Cruzadas por Agencia (Precios en Guaraníes)
    publicaciones = [
        Publicacion(
            id=1, inmueble_id=1, agencia_id=1,
            url_externa='https://www.remax.com.py/propiedades/dpto-feel-villa-morra-101',
            titulo_original='ALQUILO DPTO 2 DORM AMOBLADO EDIFICIO FEEL VILLA MORRA',
            descripcion='Hermoso departamento de 2 habitaciones en suite, balcón con parrilla y amenities.',
            tipo_operacion='alquiler', moneda_original='USD', precio_original=850.0,
            precio_pyg=6630000.0, expensas_pyg=650000.0, superficie_reportada_m2=90.0,
            imagen_url='https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=2, inmueble_id=1, agencia_id=2,
            url_externa='https://www.infocasas.com.py/alquiler-dpto-2-dorm-feel-asuncion/201',
            titulo_original='Departamento 2 Dormitorios en Edificio Feel - Villa Morra',
            descripcion='Excelente unidad en piso alto. Incluye 1 cochera. Expensas e IVA incluidos.',
            tipo_operacion='alquiler', moneda_original='PYG', precio_original=6180000.0,
            precio_pyg=6180000.0, expensas_pyg=0.0, superficie_reportada_m2=86.0,
            imagen_url='https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=3, inmueble_id=2, agencia_id=1,
            url_externa='https://www.remax.com.py/propiedades/torre-miranda-ycua-sati-102',
            titulo_original='DPTO 1 DORMITORIO ZONA SHOPPING DEL SOL - TORRE MIRANDA',
            descripcion='A pasos del Shopping del Sol y Paseo La Galería. Piso 8 con vista panorámica.',
            tipo_operacion='alquiler', moneda_original='PYG', precio_original=4200000.0,
            precio_pyg=4200000.0, expensas_pyg=450000.0, superficie_reportada_m2=56.0,
            imagen_url='https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=4, inmueble_id=2, agencia_id=2,
            url_externa='https://www.infocasas.com.py/alquiler-torre-miranda-1-dorm/202',
            titulo_original='Alquilo moderno dpto 1 dormitorio en Ycuá Satí - Torre Miranda',
            descripcion='Totalmente equipado, gimnasio, piscina en azotea y seguridad 24 hs.',
            tipo_operacion='alquiler', moneda_original='PYG', precio_original=3850000.0,
            precio_pyg=3850000.0, expensas_pyg=380000.0, superficie_reportada_m2=55.0,
            imagen_url='https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=5, inmueble_id=3, agencia_id=1,
            url_externa='https://www.remax.com.py/propiedades/casa-mburucuya-piscina-103',
            titulo_original='ALQUILO RESIDENCIA 3 DORMITORIOS CON PISCINA EN MBURUCUYA',
            descripcion='Amplia casa en barrio residencial tranquilo, quincho climatizado y piscina.',
            tipo_operacion='alquiler', moneda_original='USD', precio_original=1500.0,
            precio_pyg=11700000.0, expensas_pyg=0.0, superficie_reportada_m2=245.0,
            imagen_url='https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=6, inmueble_id=3, agencia_id=2,
            url_externa='https://www.infocasas.com.py/casa-en-alquiler-mburucuya-3-dorm/203',
            titulo_original='Hermosa Casa de 3 Habitaciones en Mburucuyá con Jardín y Piscina',
            descripcion='Ideal para familia. Cochera para 2 camionetas, área de servicio completa.',
            tipo_operacion='alquiler', moneda_original='PYG', precio_original=10900000.0,
            precio_pyg=10900000.0, expensas_pyg=0.0, superficie_reportada_m2=238.0,
            imagen_url='https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=7, inmueble_id=4, agencia_id=1,
            url_externa='https://www.remax.com.py/propiedades/duplex-luque-conmebol-104',
            titulo_original='VENDO DUPLEX A ESTRENAR 3 DORM ZONA CONMEBOL LUQUE',
            descripcion='Finas terminaciones, porcelanato, cocina amoblada y patio con parrilla.',
            tipo_operacion='venta', moneda_original='USD', precio_original=135000.0,
            precio_pyg=1053000000.0, expensas_pyg=0.0, superficie_reportada_m2=165.0,
            imagen_url='https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=8, inmueble_id=4, agencia_id=2,
            url_externa='https://www.infocasas.com.py/venta-duplex-luque-conmebol/204',
            titulo_original='En Venta Dúplex de 3 Dormitorios en suite - Luque Zona Aeropuerto',
            descripcion='Entrega inmediata, apto para crédito bancario AFD.',
            tipo_operacion='venta', moneda_original='USD', precio_original=128000.0,
            precio_pyg=998400000.0, expensas_pyg=0.0, superficie_reportada_m2=162.0,
            imagen_url='https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=9, inmueble_id=5, agencia_id=2,
            url_externa='https://www.infocasas.com.py/dpto-las-mercedes-2-dorm/205',
            titulo_original='Alquilo Dpto 2 Dormitorios en el corazón de Las Mercedes',
            descripcion='Cerca de cafés y colegios. Ambiente cálido y luminoso.',
            tipo_operacion='alquiler', moneda_original='PYG', precio_original=4500000.0,
            precio_pyg=4500000.0, expensas_pyg=350000.0, superficie_reportada_m2=95.0,
            imagen_url='https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=10, inmueble_id=6, agencia_id=1,
            url_externa='https://www.remax.com.py/propiedades/casa-lambare-yacht-106',
            titulo_original='VENDO AMPLIA RESIDENCIA EN LAMBARE ZONA YACHT',
            descripcion='4 dormitorios, amplio terreno, piscina y quincho.',
            tipo_operacion='venta', moneda_original='PYG', precio_original=1450000000.0,
            precio_pyg=1450000000.0, expensas_pyg=0.0, superficie_reportada_m2=350.0,
            imagen_url='https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=800&q=80',
            activo=True
        ),
        Publicacion(
            id=11, inmueble_id=6, agencia_id=2,
            url_externa='https://www.infocasas.com.py/venta-casa-lambare-4-dorm/206',
            titulo_original='Residencia de 4 Habitaciones en Venta - Lambaré',
            descripcion='Exclusiva propiedad en calle sin salida muy segura.',
            tipo_operacion='venta', moneda_original='PYG', precio_original=1390000000.0,
            precio_pyg=1390000000.0, expensas_pyg=0.0, superficie_reportada_m2=348.0,
            imagen_url='https://images.unsplash.com/photo-1570129477492-45c003edd2be?auto=format&fit=crop&w=800&q=80',
            activo=True
        )
    ]
    db.session.add_all(publicaciones)
    db.session.flush()

    # 9. Movimiento Transaccional de Ejemplo (Cabecera y Detalle - Requisito 8.1)
    solicitud = SolicitudVisita(
        id=1,
        usuario_id=2,
        inmueble_id=1,
        fecha_visita_propuesta=date.today() + timedelta(days=3),
        horario_preferido='Mañana (09:00 - 12:00)',
        estado='PENDIENTE',
        observaciones='Deseo coordinar visita con ambas agencias para verificar diferencia de Gs. 450.000 y expensas.'
    )
    db.session.add(solicitud)
    db.session.flush()

    detalles = [
        SolicitudDetalle(
            solicitud_id=1, publicacion_id=2,
            precio_congelado_pyg=6180000.0, expensas_congeladas_pyg=0.0,
            comentario_agencia='Oferta más económica detectada en InfoCasas'
        ),
        SolicitudDetalle(
            solicitud_id=1, publicacion_id=1,
            precio_congelado_pyg=6630000.0, expensas_congeladas_pyg=650000.0,
            comentario_agencia='Oferta en RE/MAX para contrastar condiciones'
        )
    ]
    db.session.add_all(detalles)
    db.session.commit()
