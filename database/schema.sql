-- =============================================================================
-- ESQUEMA DE BASE DE DATOS: METABUSCADOR INMOBILIARIO PARAGUAY
-- Normalización: 3ra Forma Normal (3FN) | Total: 10 Tablas Relacionadas
-- Motor compatible: PostgreSQL 15+ / Supabase
-- =============================================================================

-- Limpieza previa de tablas (en orden inverso de dependencias) para recreación limpia
DROP TABLE IF EXISTS solicitud_detalles CASCADE;
DROP TABLE IF EXISTS solicitudes_visita CASCADE;
DROP TABLE IF EXISTS publicaciones CASCADE;
DROP TABLE IF EXISTS inmuebles CASCADE;
DROP TABLE IF EXISTS agencias CASCADE;
DROP TABLE IF EXISTS tipos_inmueble CASCADE;
DROP TABLE IF EXISTS barrios CASCADE;
DROP TABLE IF EXISTS ciudades CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS roles CASCADE;

-- -----------------------------------------------------------------------------
-- 1. TABLA: roles
-- Almacena los perfiles de acceso al sistema (Ej: Administrador, Cliente).
-- Cumple 3FN al separar los atributos del rol de la tabla de usuarios.
-- -----------------------------------------------------------------------------
CREATE TABLE roles (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(200)
);

-- -----------------------------------------------------------------------------
-- 2. TABLA: usuarios
-- Gestiona las cuentas para el Login (Requisito 8.2) y auditoría de movimientos.
-- Relación N:1 con roles.
-- -----------------------------------------------------------------------------
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,
    rol_id INT NOT NULL REFERENCES roles(id) ON DELETE RESTRICT,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    telefono VARCHAR(30),
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 3. TABLA: ciudades
-- Catálogo maestro de municipios (Asunción y Gran Asunción).
-- Cumple 3FN evitando repetir el nombre de la ciudad y departamento en barrios.
-- -----------------------------------------------------------------------------
CREATE TABLE ciudades (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    departamento VARCHAR(100) NOT NULL DEFAULT 'Central'
);

-- -----------------------------------------------------------------------------
-- 4. TABLA: barrios
-- Catálogo maestro de barrios con coordenadas centroides para el mapa Leaflet.
-- Relación N:1 con ciudades.
-- -----------------------------------------------------------------------------
CREATE TABLE barrios (
    id SERIAL PRIMARY KEY,
    ciudad_id INT NOT NULL REFERENCES ciudades(id) ON DELETE RESTRICT,
    nombre VARCHAR(100) NOT NULL,
    lat_centroide NUMERIC(9, 6) NOT NULL,
    lon_centroide NUMERIC(9, 6) NOT NULL,
    UNIQUE (ciudad_id, nombre)
);

-- -----------------------------------------------------------------------------
-- 5. TABLA: tipos_inmueble
-- Clasificación física de la propiedad (Departamento, Casa, Dúplex).
-- Cumple 3FN desacoplando la descripción del tipo de la tabla de inmuebles.
-- -----------------------------------------------------------------------------
CREATE TABLE tipos_inmueble (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(50) NOT NULL UNIQUE,
    descripcion VARCHAR(200)
);

-- -----------------------------------------------------------------------------
-- 6. TABLA: agencias
-- Portales o empresas inmobiliarias de origen (Remax, InfoCasas, etc.).
-- Administrable desde el módulo de Mantenimientos (Requisito 8.4).
-- -----------------------------------------------------------------------------
CREATE TABLE agencias (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    sitio_web VARCHAR(255) NOT NULL,
    logo_url VARCHAR(500),
    telefono_contacto VARCHAR(50),
    activo BOOLEAN DEFAULT TRUE,
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 7. TABLA: inmuebles
-- Entidad física unificada/deduplicada. Representa la propiedad real sin
-- importar cuántas inmobiliarias la publiquen.
-- Relación N:1 con tipos_inmueble y N:1 con barrios.
-- -----------------------------------------------------------------------------
CREATE TABLE inmuebles (
    id SERIAL PRIMARY KEY,
    tipo_inmueble_id INT NOT NULL REFERENCES tipos_inmueble(id) ON DELETE RESTRICT,
    barrio_id INT NOT NULL REFERENCES barrios(id) ON DELETE RESTRICT,
    titulo_canonico VARCHAR(255) NOT NULL,
    nombre_edificio VARCHAR(150),          -- Clave para agrupar departamentos
    dormitorios INT NOT NULL DEFAULT 1,
    banos INT NOT NULL DEFAULT 1,
    estacionamientos INT DEFAULT 0,
    superficie_m2 NUMERIC(8, 2) NOT NULL,
    latitud NUMERIC(9, 6),                 -- Si es nulo, usa el centroide del barrio
    longitud NUMERIC(9, 6),
    creado_en TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 8. TABLA: publicaciones
-- Avisos individuales por agencia asociados a un inmueble físico (Comparación).
-- Permite comparar precios, expensas y superficies entre distintas agencias.
-- Relación N:1 con inmuebles y N:1 con agencias.
-- -----------------------------------------------------------------------------
CREATE TABLE publicaciones (
    id SERIAL PRIMARY KEY,
    inmueble_id INT NOT NULL REFERENCES inmuebles(id) ON DELETE CASCADE,
    agencia_id INT NOT NULL REFERENCES agencias(id) ON DELETE RESTRICT,
    url_externa VARCHAR(500) NOT NULL UNIQUE,
    titulo_original VARCHAR(255) NOT NULL,
    descripcion TEXT,
    tipo_operacion VARCHAR(20) NOT NULL CHECK (tipo_operacion IN ('alquiler', 'venta')),
    moneda_original VARCHAR(3) NOT NULL DEFAULT 'PYG' CHECK (moneda_original IN ('PYG', 'USD')),
    precio_original NUMERIC(15, 2) NOT NULL,
    precio_pyg NUMERIC(15, 2) NOT NULL,    -- Precio siempre normalizado en Guaraníes
    expensas_pyg NUMERIC(12, 2) DEFAULT 0, -- Expensas mensuales en Guaraníes
    superficie_reportada_m2 NUMERIC(8, 2), -- M2 según esta agencia en particular
    imagen_url VARCHAR(500),
    activo BOOLEAN DEFAULT TRUE,           -- Baja automática si el aviso cae (404)
    ultima_extraccion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- -----------------------------------------------------------------------------
-- 9. TABLA: solicitudes_visita (CABECERA DEL MOVIMIENTO - Requisito 8.1)
-- Registra la operación transaccional cuando un usuario agenda/solicita visitar
-- un inmueble tras comparar sus ofertas.
-- -----------------------------------------------------------------------------
CREATE TABLE solicitudes_visita (
    id SERIAL PRIMARY KEY,
    usuario_id INT NOT NULL REFERENCES usuarios(id) ON DELETE RESTRICT,
    inmueble_id INT NOT NULL REFERENCES inmuebles(id) ON DELETE RESTRICT,
    fecha_solicitud TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    fecha_visita_propuesta DATE NOT NULL,
    horario_preferido VARCHAR(50) NOT NULL, -- Ej: 'Mañana (09:00 - 12:00)'
    estado VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado IN ('PENDIENTE', 'CONFIRMADA', 'REALIZADA', 'CANCELADA')),
    observaciones TEXT
);

-- -----------------------------------------------------------------------------
-- 10. TABLA: solicitud_detalles (DETALLE DEL MOVIMIENTO - Requisito 8.1)
-- Detalla qué publicaciones/agencias específicas seleccionó el usuario en su
-- solicitud, congelando el precio y expensas vigentes en ese momento.
-- -----------------------------------------------------------------------------
CREATE TABLE solicitud_detalles (
    id SERIAL PRIMARY KEY,
    solicitud_id INT NOT NULL REFERENCES solicitudes_visita(id) ON DELETE CASCADE,
    publicacion_id INT NOT NULL REFERENCES publicaciones(id) ON DELETE RESTRICT,
    precio_congelado_pyg NUMERIC(15, 2) NOT NULL,
    expensas_congeladas_pyg NUMERIC(12, 2) NOT NULL DEFAULT 0,
    comentario_agencia VARCHAR(255),
    UNIQUE (solicitud_id, publicacion_id)
);

-- -----------------------------------------------------------------------------
-- ÍNDICES PARA OPTIMIZACIÓN DE BÚSQUEDAS Y FILTROS
-- -----------------------------------------------------------------------------
-- Acelera el filtrado por barrio y tipo de propiedad en el buscador
CREATE INDEX idx_inmuebles_barrio_tipo ON inmuebles(barrio_id, tipo_inmueble_id);

-- Acelera el ordenamiento por precio en Guaraníes y filtrado por operación
CREATE INDEX idx_publicaciones_busqueda ON publicaciones(tipo_operacion, activo, precio_pyg);

-- Acelera la consulta de publicaciones asociadas a un mismo inmueble físico
CREATE INDEX idx_publicaciones_inmueble ON publicaciones(inmueble_id);

-- Acelera el historial de movimientos por usuario
CREATE INDEX idx_solicitudes_usuario ON solicitudes_visita(usuario_id, estado);
