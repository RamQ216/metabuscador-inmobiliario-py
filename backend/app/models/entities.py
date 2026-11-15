from datetime import datetime, date
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# Instancia global del ORM SQLAlchemy
db = SQLAlchemy()


# =============================================================================
# 1. MODELO: Rol (Tabla 'roles')
# =============================================================================
class Rol(db.Model):
    """Representa el perfil de acceso del usuario (Administrador o Cliente) en 3FN."""
    __tablename__ = 'roles'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(200))

    # Relación 1:N hacia Usuarios
    usuarios = db.relationship('Usuario', back_populates='rol', lazy=True)

    def to_dict(self):
        """Convierte el rol a diccionario JSON para respuestas de la API."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion
        }


# =============================================================================
# 2. MODELO: Usuario (Tabla 'usuarios') - Requisito 8.2 (Login)
# =============================================================================
class Usuario(db.Model):
    """Almacena las credenciales y datos personales de los usuarios del sistema."""
    __tablename__ = 'usuarios'

    id = db.Column(db.Integer, primary_key=True)
    rol_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    apellido = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    telefono = db.Column(db.String(30))
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones explícitas (Requisito 4.2)
    rol = db.relationship('Rol', back_populates='usuarios')
    solicitudes = db.relationship('SolicitudVisita', back_populates='usuario', lazy=True)

    def set_password(self, raw_password):
        """Encripta la contraseña con algoritmo PBKDF2/Scrypt antes de guardarla."""
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        """Verifica la contraseña exclusivamente mediante comparación criptográfica de hash."""
        if not self.password_hash or not raw_password:
            return False
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self):
        """Serializa los datos del usuario sin exponer la contraseña."""
        return {
            'id': self.id,
            'rol_id': self.rol_id,
            'rol_nombre': self.rol.nombre if self.rol else None,
            'nombre': self.nombre,
            'apellido': self.apellido,
            'nombre_completo': f"{self.nombre} {self.apellido}",
            'email': self.email,
            'telefono': self.telefono,
            'activo': self.activo
        }


# =============================================================================
# 3. MODELO: Ciudad (Tabla 'ciudades')
# =============================================================================
class Ciudad(db.Model):
    """Catálogo maestro de ciudades (Asunción y municipios de Gran Asunción)."""
    __tablename__ = 'ciudades'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    departamento = db.Column(db.String(100), nullable=False, default='Central')

    # Relación 1:N con Barrios
    barrios = db.relationship('Barrio', back_populates='ciudad', lazy=True)

    def to_dict(self):
        """Serializa los datos de la ciudad."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'departamento': self.departamento
        }


# =============================================================================
# 4. MODELO: Barrio (Tabla 'barrios')
# =============================================================================
class Barrio(db.Model):
    """Catálogo maestro de barrios con coordenadas centroides para el mapa."""
    __tablename__ = 'barrios'

    id = db.Column(db.Integer, primary_key=True)
    ciudad_id = db.Column(db.Integer, db.ForeignKey('ciudades.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    lat_centroide = db.Column(db.Float, nullable=False)
    lon_centroide = db.Column(db.Float, nullable=False)

    # Relaciones hacia Ciudad e Inmuebles
    ciudad = db.relationship('Ciudad', back_populates='barrios')
    inmuebles = db.relationship('Inmueble', back_populates='barrio', lazy=True)

    def to_dict(self):
        """Serializa el barrio junto con el nombre de su ciudad."""
        return {
            'id': self.id,
            'ciudad_id': self.ciudad_id,
            'ciudad_nombre': self.ciudad.nombre if self.ciudad else None,
            'nombre': self.nombre,
            'lat_centroide': float(self.lat_centroide),
            'lon_centroide': float(self.lon_centroide)
        }


# =============================================================================
# 5. MODELO: TipoInmueble (Tabla 'tipos_inmueble')
# =============================================================================
class TipoInmueble(db.Model):
    """Clasificación del inmueble (Departamento, Casa, Dúplex) normalizada en 3FN."""
    __tablename__ = 'tipos_inmueble'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False, unique=True)
    descripcion = db.Column(db.String(200))

    # Relación 1:N hacia Inmuebles
    inmuebles = db.relationship('Inmueble', back_populates='tipo_inmueble', lazy=True)

    def to_dict(self):
        """Serializa el tipo de inmueble."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'descripcion': self.descripcion
        }


# =============================================================================
# 6. MODELO: Agencia (Tabla 'agencias')
# =============================================================================
class Agencia(db.Model):
    """Representa una inmobiliaria o portal fuente (RE/MAX, InfoCasas, etc.)."""
    __tablename__ = 'agencias'

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False, unique=True)
    sitio_web = db.Column(db.String(255), nullable=False)
    logo_url = db.Column(db.String(500))
    telefono_contacto = db.Column(db.String(50))
    activo = db.Column(db.Boolean, default=True)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relación 1:N con Publicaciones
    publicaciones = db.relationship('Publicacion', back_populates='agencia', lazy=True)

    def to_dict(self):
        """Serializa los datos de la agencia inmobiliaria."""
        return {
            'id': self.id,
            'nombre': self.nombre,
            'sitio_web': self.sitio_web,
            'logo_url': self.logo_url,
            'telefono_contacto': self.telefono_contacto,
            'activo': self.activo
        }


# =============================================================================
# 7. MODELO: Inmueble (Tabla 'inmuebles')
# =============================================================================
class Inmueble(db.Model):
    """
    Entidad física unificada/deduplicada. Agrupa todas las publicaciones que
    corresponden a la misma casa o departamento real.
    """
    __tablename__ = 'inmuebles'

    id = db.Column(db.Integer, primary_key=True)
    tipo_inmueble_id = db.Column(db.Integer, db.ForeignKey('tipos_inmueble.id'), nullable=False)
    barrio_id = db.Column(db.Integer, db.ForeignKey('barrios.id'), nullable=False)
    titulo_canonico = db.Column(db.String(255), nullable=False)
    nombre_edificio = db.Column(db.String(150))
    dormitorios = db.Column(db.Integer, nullable=False, default=1)
    banos = db.Column(db.Integer, nullable=False, default=1)
    estacionamientos = db.Column(db.Integer, default=0)
    superficie_m2 = db.Column(db.Float, nullable=False)
    latitud = db.Column(db.Float)
    longitud = db.Column(db.Float)
    creado_en = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones con tablas maestras y secundarias
    tipo_inmueble = db.relationship('TipoInmueble', back_populates='inmuebles')
    barrio = db.relationship('Barrio', back_populates='inmuebles')
    publicaciones = db.relationship('Publicacion', back_populates='inmueble', cascade='all, delete-orphan', lazy=True)
    solicitudes = db.relationship('SolicitudVisita', back_populates='inmueble', lazy=True)

    def to_summary_dict(self, active_listings=None):
        """
        Genera el resumen de la propiedad para las tarjetas del buscador,
        calculando el rango de precios (Desde/Hasta) y el ahorro potencial en Guaraníes.
        """
        listings = active_listings if active_listings is not None else [p for p in self.publicaciones if p.activo]
        precios = [float(p.precio_pyg) for p in listings] if listings else [0.0]
        precio_min = min(precios)
        precio_max = max(precios)

        # Usa las coordenadas propias o el centroide del barrio como respaldo
        lat = self.latitud if self.latitud is not None else (self.barrio.lat_centroide if self.barrio else -25.2867)
        lon = self.longitud if self.longitud is not None else (self.barrio.lon_centroide if self.barrio else -57.6470)

        return {
            'id': self.id,
            'titulo_canonico': self.titulo_canonico,
            'nombre_edificio': self.nombre_edificio,
            'tipo_inmueble_id': self.tipo_inmueble_id,
            'tipo_inmueble': self.tipo_inmueble.nombre if self.tipo_inmueble else '',
            'barrio_id': self.barrio_id,
            'barrio': self.barrio.nombre if self.barrio else '',
            'ciudad_id': self.barrio.ciudad_id if self.barrio else None,
            'ciudad': self.barrio.ciudad.nombre if (self.barrio and self.barrio.ciudad) else '',
            'dormitorios': self.dormitorios,
            'banos': self.banos,
            'estacionamientos': self.estacionamientos,
            'superficie_m2': float(self.superficie_m2),
            'latitud': float(lat),
            'longitud': float(lon),
            'cantidad_agencias': len(listings),
            'es_duplicado': len(listings) > 1,
            'precio_min_pyg': precio_min,
            'precio_max_pyg': precio_max,
            'diferencia_pyg': precio_max - precio_min,
            'tipo_operacion': listings[0].tipo_operacion if listings else 'alquiler',
            'imagen_principal': listings[0].imagen_url if listings else None,
            'publicaciones': [p.to_dict() for p in sorted(listings, key=lambda x: x.precio_pyg)]
        }


# =============================================================================
# 8. MODELO: Publicacion (Tabla 'publicaciones')
# =============================================================================
class Publicacion(db.Model):
    """Representa el aviso individual de una agencia sobre un inmueble específico."""
    __tablename__ = 'publicaciones'

    id = db.Column(db.Integer, primary_key=True)
    inmueble_id = db.Column(db.Integer, db.ForeignKey('inmuebles.id'), nullable=False)
    agencia_id = db.Column(db.Integer, db.ForeignKey('agencias.id'), nullable=False)
    url_externa = db.Column(db.String(500), nullable=False, unique=True)
    titulo_original = db.Column(db.String(255), nullable=False)
    descripcion = db.Column(db.Text)
    tipo_operacion = db.Column(db.String(20), nullable=False, default='alquiler')
    moneda_original = db.Column(db.String(3), nullable=False, default='PYG')
    precio_original = db.Column(db.Float, nullable=False)
    precio_pyg = db.Column(db.Float, nullable=False)
    expensas_pyg = db.Column(db.Float, default=0.0)
    superficie_reportada_m2 = db.Column(db.Float)
    imagen_url = db.Column(db.String(500))
    activo = db.Column(db.Boolean, default=True)
    ultima_extraccion = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones hacia Inmueble y Agencia
    inmueble = db.relationship('Inmueble', back_populates='publicaciones')
    agencia = db.relationship('Agencia', back_populates='publicaciones')

    def to_dict(self):
        """Serializa los datos de la publicación para la tabla comparativa."""
        return {
            'id': self.id,
            'inmueble_id': self.inmueble_id,
            'agencia_id': self.agencia_id,
            'agencia_nombre': self.agencia.nombre if self.agencia else '',
            'agencia_logo': self.agencia.logo_url if self.agencia else '',
            'agencia_telefono': self.agencia.telefono_contacto if self.agencia else '',
            'url_externa': self.url_externa,
            'titulo_original': self.titulo_original,
            'descripcion': self.descripcion,
            'tipo_operacion': self.tipo_operacion,
            'moneda_original': self.moneda_original,
            'precio_original': float(self.precio_original),
            'precio_pyg': float(self.precio_pyg),
            'expensas_pyg': float(self.expensas_pyg or 0),
            'costo_total_mensual_pyg': float(self.precio_pyg) + float(self.expensas_pyg or 0),
            'superficie_reportada_m2': float(self.superficie_reportada_m2 or 0),
            'imagen_url': self.imagen_url,
            'activo': self.activo,
            'ultima_extraccion': self.ultima_extraccion.strftime('%Y-%m-%d %H:%M') if self.ultima_extraccion else None
        }


# =============================================================================
# 9. MODELO: SolicitudVisita (Tabla 'solicitudes_visita') - Requisito 8.1
# =============================================================================
class SolicitudVisita(db.Model):
    """Cabecera del Movimiento Transaccional: Solicitud de visita comparada."""
    __tablename__ = 'solicitudes_visita'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    inmueble_id = db.Column(db.Integer, db.ForeignKey('inmuebles.id'), nullable=False)
    fecha_solicitud = db.Column(db.DateTime, default=datetime.utcnow)
    fecha_visita_propuesta = db.Column(db.Date, nullable=False, default=date.today)
    horario_preferido = db.Column(db.String(50), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default='PENDIENTE')
    observaciones = db.Column(db.Text)

    # Relaciones con Usuario, Inmueble y sus Detalles
    usuario = db.relationship('Usuario', back_populates='solicitudes')
    inmueble = db.relationship('Inmueble', back_populates='solicitudes')
    detalles = db.relationship('SolicitudDetalle', back_populates='solicitud', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        """Serializa la cabecera y todos los ítems de detalle del movimiento."""
        return {
            'id': self.id,
            'usuario_id': self.usuario_id,
            'usuario_nombre': f"{self.usuario.nombre} {self.usuario.apellido}" if self.usuario else '',
            'usuario_email': self.usuario.email if self.usuario else '',
            'inmueble_id': self.inmueble_id,
            'inmueble_titulo': self.inmueble.titulo_canonico if self.inmueble else '',
            'barrio': self.inmueble.barrio.nombre if (self.inmueble and self.inmueble.barrio) else '',
            'fecha_solicitud': self.fecha_solicitud.strftime('%Y-%m-%d %H:%M') if self.fecha_solicitud else '',
            'fecha_visita_propuesta': self.fecha_visita_propuesta.strftime('%Y-%m-%d') if self.fecha_visita_propuesta else '',
            'horario_preferido': self.horario_preferido,
            'estado': self.estado,
            'observaciones': self.observaciones,
            'detalles': [d.to_dict() for d in self.detalles]
        }


# =============================================================================
# 10. MODELO: SolicitudDetalle (Tabla 'solicitud_detalles') - Requisito 8.1
# =============================================================================
class SolicitudDetalle(db.Model):
    """Detalle del Movimiento Transaccional: Agencias seleccionadas y precios congelados."""
    __tablename__ = 'solicitud_detalles'

    id = db.Column(db.Integer, primary_key=True)
    solicitud_id = db.Column(db.Integer, db.ForeignKey('solicitudes_visita.id'), nullable=False)
    publicacion_id = db.Column(db.Integer, db.ForeignKey('publicaciones.id'), nullable=False)
    precio_congelado_pyg = db.Column(db.Float, nullable=False)
    expensas_congeladas_pyg = db.Column(db.Float, nullable=False, default=0.0)
    comentario_agencia = db.Column(db.String(255))

    # Relaciones hacia la Cabecera y la Publicación seleccionada
    solicitud = db.relationship('SolicitudVisita', back_populates='detalles')
    publicacion = db.relationship('Publicacion')

    def to_dict(self):
        """Serializa un ítem del detalle de la solicitud de visita."""
        return {
            'id': self.id,
            'solicitud_id': self.solicitud_id,
            'publicacion_id': self.publicacion_id,
            'agencia_nombre': self.publicacion.agencia.nombre if (self.publicacion and self.publicacion.agencia) else '',
            'url_externa': self.publicacion.url_externa if self.publicacion else '',
            'precio_congelado_pyg': float(self.precio_congelado_pyg),
            'expensas_congeladas_pyg': float(self.expensas_congeladas_pyg),
            'comentario_agencia': self.comentario_agencia
        }
