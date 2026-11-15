-- =============================================================================
-- DATOS SEMILLA (SEED): METABUSCADOR INMOBILIARIO PARAGUAY
-- Carga inicial de catálogos, usuarios de prueba, propiedades y comparativas
-- =============================================================================

-- 1. Carga de Roles del Sistema
INSERT INTO roles (id, nombre, descripcion) VALUES
(1, 'Administrador', 'Acceso total a mantenimientos (CRUDs), scrapers y gestión de solicitudes'),
(2, 'Cliente', 'Acceso al metabuscador, comparador cruzado y creación de solicitudes de visita');

-- 2. Carga de Usuarios Iniciales (Contraseña texto plano demostrativa o hash para pruebas: '123456')
-- Nota: El backend verificará hashes werkzeug o texto de prueba inicial para facilitar evaluación docente
INSERT INTO usuarios (id, rol_id, nombre, apellido, email, password_hash, telefono, activo) VALUES
(1, 1, 'Carlos', 'Administrador', 'admin@inmueblespy.com', 'admin123', '0981-100200', TRUE),
(2, 2, 'María', 'González', 'maria@gmail.com', 'cliente123', '0971-555444', TRUE);

-- 3. Carga de Ciudades (Asunción y Gran Asunción)
INSERT INTO ciudades (id, nombre, departamento) VALUES
(1, 'Asunción', 'Capital'),
(2, 'Luque', 'Central'),
(3, 'San Lorenzo', 'Central'),
(4, 'Fernando de la Mora', 'Central'),
(5, 'Lambaré', 'Central'),
(6, 'Mariano Roque Alonso', 'Central');

-- 4. Carga del Catálogo Maestro de Barrios con Coordenadas Centroides Oficiales
INSERT INTO barrios (id, ciudad_id, nombre, lat_centroide, lon_centroide) VALUES
(1, 1, 'Villa Morra', -25.294700, -57.580600),
(2, 1, 'Ycuá Satí', -25.287800, -57.564400),
(3, 1, 'Las Lomas (Carmelitas)', -25.278900, -57.569200),
(4, 1, 'Mburucuyá', -25.272500, -57.558300),
(5, 1, 'Recoleta', -25.298100, -57.591900),
(6, 1, 'Las Mercedes', -25.284200, -57.611400),
(7, 2, 'Cuarto Barrio', -25.266700, -57.492500),
(8, 2, 'Zona Conmebol / Aeropuerto', -25.258100, -57.523600),
(9, 4, 'Zona Norte', -25.313300, -57.551400),
(10, 5, 'Canal 13 / Valle Apu''a', -25.341100, -57.618600);

-- 5. Carga de Tipos de Inmueble (Requisito: Departamentos y Casas incluidos)
INSERT INTO tipos_inmueble (id, nombre, descripcion) VALUES
(1, 'Departamento', 'Unidad residencial en edificio de altura con áreas comunes'),
(2, 'Casa', 'Vivienda unifamiliar independiente con terreno propio'),
(3, 'Dúplex', 'Vivienda de dos plantas pareada o en condominio');

-- 6. Carga de Agencias Inmobiliarias (Fuentes elegidas: Remax + InfoCasas)
INSERT INTO agencias (id, nombre, sitio_web, logo_url, telefono_contacto, activo) VALUES
(1, 'RE/MAX Paraguay', 'https://www.remax.com.py', 'https://upload.wikimedia.org/wikipedia/commons/thumb/0/0c/ReMax_logo.svg/320px-ReMax_logo.svg.png', '021-600700', TRUE),
(2, 'InfoCasas Paraguay', 'https://www.infocasas.com.py', 'https://cdn2.infocasas.com.uy/web/5b4f7c2685386_infocasas-logo.png', '021-300400', TRUE);

-- 7. Carga de Inmuebles Físicos Deduplicados (Casas y Departamentos)
INSERT INTO inmuebles (id, tipo_inmueble_id, barrio_id, titulo_canonico, nombre_edificio, dormitorios, banos, estacionamientos, superficie_m2, latitud, longitud) VALUES
(1, 1, 1, 'Departamento de 2 Dormitorios en Edificio Feel Asunción', 'Edificio Feel', 2, 2, 1, 88.00, -25.295100, -57.579800),
(2, 1, 2, 'Departamento de 1 Dormitorio en Torre Miranda - Zona Shopping del Sol', 'Torre Miranda', 1, 1, 1, 56.00, -25.286900, -57.563900),
(3, 2, 4, 'Residencia Familiar con Piscina en Barrio Mburucuyá', NULL, 3, 3, 2, 240.00, -25.273100, -57.557900),
(4, 3, 8, 'Dúplex Moderno a Estrenar en Zona Conmebol - Luque', NULL, 3, 3, 2, 165.00, -25.258900, -57.522800),
(5, 1, 6, 'Departamento Amplio en Las Mercedes sobre Padre Cardozo', 'Edificio Las Mercedes Plaza', 2, 2, 1, 95.00, -25.284500, -57.610900),
(6, 2, 10, 'Casa Quinta Residencial en Lambaré Zona Yacht', NULL, 4, 4, 3, 350.00, -25.342000, -57.619200);

-- 8. Carga de Publicaciones Cruzadas (Demuestra el ahorro entre agencias en Guaraníes)
INSERT INTO publicaciones (id, inmueble_id, agencia_id, url_externa, titulo_original, descripcion, tipo_operacion, moneda_original, precio_original, precio_pyg, expensas_pyg, superficie_reportada_m2, imagen_url, activo) VALUES
-- Inmueble 1: Publicado en Remax y en InfoCasas con Gs. 450.000 de diferencia
(1, 1, 1, 'https://www.remax.com.py/propiedades/dpto-feel-villa-morra-101', 'ALQUILO DPTO 2 DORM AMOBLADO EDIFICIO FEEL VILLA MORRA', 'Hermoso departamento de 2 habitaciones en suite, balcón con parrilla, amenities de primer nivel.', 'alquiler', 'USD', 850.00, 6630000.00, 650000.00, 90.00, 'https://images.unsplash.com/photo-1522708323590-d24dbb6b0267?auto=format&fit=crop&w=800&q=80', TRUE),
(2, 1, 2, 'https://www.infocasas.com.py/alquiler-dpto-2-dorm-feel-asuncion/201', 'Departamento 2 Dormitorios en Edificio Feel - Villa Morra', 'Excelente unidad en piso alto. Incluye 1 cochera. Expensas e IVA incluidos en el precio.', 'alquiler', 'PYG', 6180000.00, 6180000.00, 0.00, 86.00, 'https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?auto=format&fit=crop&w=800&q=80', TRUE),

-- Inmueble 2: Publicado en ambas agencias con diferencia de precio y expensas
(3, 2, 1, 'https://www.remax.com.py/propiedades/torre-miranda-ycua-sati-102', 'DPTO 1 DORMITORIO ZONA SHOPPING DEL SOL - TORRE MIRANDA', 'A pasos del Shopping del Sol y Paseo La Galería. Piso 8 con vista panorámica.', 'alquiler', 'PYG', 4200000.00, 4200000.00, 450000.00, 56.00, 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=800&q=80', TRUE),
(4, 2, 2, 'https://www.infocasas.com.py/alquiler-torre-miranda-1-dorm/202', 'Alquilo moderno dpto 1 dormitorio en Ycuá Satí - Torre Miranda', 'Totalmente equipado, gimnasio, piscina en azotea y seguridad 24 hs.', 'alquiler', 'PYG', 3850000.00, 3850000.00, 380000.00, 55.00, 'https://images.unsplash.com/photo-1493809842364-78817add7ffb?auto=format&fit=crop&w=800&q=80', TRUE),

-- Inmueble 3: Casa en Mburucuyá publicada en ambas agencias
(5, 3, 1, 'https://www.remax.com.py/propiedades/casa-mburucuya-piscina-103', 'ALQUILO RESIDENCIA 3 DORMITORIOS CON PISCINA EN MBURUCUYA', 'Amplia casa en barrio residencial tranquilo, quincho climatizado, patio empastado y piscina.', 'alquiler', 'USD', 1500.00, 11700000.00, 0.00, 245.00, 'https://images.unsplash.com/photo-1600596542815-ffad4c1539a9?auto=format&fit=crop&w=800&q=80', TRUE),
(6, 3, 2, 'https://www.infocasas.com.py/casa-en-alquiler-mburucuya-3-dorm/203', 'Hermosa Casa de 3 Habitaciones en Mburucuyá con Jardín y Piscina', 'Ideal para familia o diplomáticos. Cochera para 2 camionetas, área de servicio completa.', 'alquiler', 'PYG', 10900000.00, 10900000.00, 0.00, 238.00, 'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=800&q=80', TRUE),

-- Inmueble 4: Dúplex en Venta en Luque publicado en ambas agencias
(7, 4, 1, 'https://www.remax.com.py/propiedades/duplex-luque-conmebol-104', 'VENDO DUPLEX A ESTRENAR 3 DORM ZONA CONMEBOL LUQUE', 'Finas terminaciones, porcelanato, cocina amoblada Achon y pequeño patio con parrilla.', 'venta', 'USD', 135000.00, 1053000000.00, 0.00, 165.00, 'https://images.unsplash.com/photo-1512917774080-9991f1c4c750?auto=format&fit=crop&w=800&q=80', TRUE),
(8, 4, 2, 'https://www.infocasas.com.py/venta-duplex-luque-conmebol/204', 'En Venta Dúplex de 3 Dormitorios en suite - Luque Zona Aeropuerto', 'Entrega inmediata, apto para crédito bancario AFD.', 'venta', 'USD', 128000.00, 998400000.00, 0.00, 162.00, 'https://images.unsplash.com/photo-1580587771525-78b9dba3b914?auto=format&fit=crop&w=800&q=80', TRUE),

-- Inmueble 5: Publicación única en Las Mercedes
(9, 5, 2, 'https://www.infocasas.com.py/dpto-las-mercedes-2-dorm/205', 'Alquilo Dpto 2 Dormitorios en el corazón de Las Mercedes', 'Cerca de cafés y colegios. Ambiente cálido y luminoso.', 'alquiler', 'PYG', 4500000.00, 4500000.00, 350000.00, 95.00, 'https://images.unsplash.com/photo-1484154218962-a197022b5858?auto=format&fit=crop&w=800&q=80', TRUE),

-- Inmueble 6: Casa en Venta en Lambaré publicada en ambas agencias
(10, 6, 1, 'https://www.remax.com.py/propiedades/casa-lambare-yacht-106', 'VENDO AMPLIA RESIDENCIA EN LAMBARE ZONA YACHT', '4 dormitorios, amplio terreno, piscina y quincho.', 'venta', 'PYG', 1450000000.00, 1450000000.00, 0.00, 350.00, 'https://images.unsplash.com/photo-1564013799919-ab600027ffc6?auto=format&fit=crop&w=800&q=80', TRUE),
(11, 6, 2, 'https://www.infocasas.com.py/venta-casa-lambare-4-dorm/206', 'Residencia de 4 Habitaciones en Venta - Lambaré', 'Exclusiva propiedad en calle sin salida muy segura.', 'venta', 'PYG', 1390000000.00, 1390000000.00, 0.00, 348.00, 'https://images.unsplash.com/photo-1570129477492-45c003edd2be?auto=format&fit=crop&w=800&q=80', TRUE);

-- 9. Ejemplo de Movimiento Transaccional Registrado (Solicitud de Visita Comparada)
INSERT INTO solicitudes_visita (id, usuario_id, inmueble_id, fecha_visita_propuesta, horario_preferido, estado, observaciones) VALUES
(1, 2, 1, CURRENT_DATE + INTERVAL '3 days', 'Mañana (09:00 - 12:00)', 'PENDIENTE', 'Deseo coordinar visita con ambas agencias para verificar por qué una incluye expensas y la otra no.');

-- 10. Detalle del Movimiento Transaccional
INSERT INTO solicitud_detalles (id, solicitud_id, publicacion_id, precio_congelado_pyg, expensas_congeladas_pyg, comentario_agencia) VALUES
(1, 1, 2, 6180000.00, 0.00, 'Oferta más económica detectada en InfoCasas (ahorro Gs. 450.000)'),
(2, 1, 1, 6630000.00, 650000.00, 'Oferta en RE/MAX para contrastar amoblamiento incluido');

-- Sincronización de secuencias de IDs autoincrementales (PostgreSQL)
SELECT setval('roles_id_seq', (SELECT MAX(id) FROM roles));
SELECT setval('usuarios_id_seq', (SELECT MAX(id) FROM usuarios));
SELECT setval('ciudades_id_seq', (SELECT MAX(id) FROM ciudades));
SELECT setval('barrios_id_seq', (SELECT MAX(id) FROM barrios));
SELECT setval('tipos_inmueble_id_seq', (SELECT MAX(id) FROM tipos_inmueble));
SELECT setval('agencias_id_seq', (SELECT MAX(id) FROM agencias));
SELECT setval('inmuebles_id_seq', (SELECT MAX(id) FROM inmuebles));
SELECT setval('publicaciones_id_seq', (SELECT MAX(id) FROM publicaciones));
SELECT setval('solicitudes_visita_id_seq', (SELECT MAX(id) FROM solicitudes_visita));
SELECT setval('solicitud_detalles_id_seq', (SELECT MAX(id) FROM solicitud_detalles));
