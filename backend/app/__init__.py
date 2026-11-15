import os
from flask import Flask, send_from_directory, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import HTTPException
from app.config import Config
from app.models import db
from app.services.seeder import inicializar_datos_semilla
from app.routes.auth_routes import auth_bp
from app.routes.search_routes import search_bp
from app.routes.movement_routes import movement_bp
from app.routes.maintenance_routes import maintenance_bp


def create_app():
    """
    Fábrica de aplicación Flask: inicializa la base de datos, aplica cabeceras de
    seguridad OWASP, registra manejadores globales de error JSON y sirve el frontend.
    """
    frontend_folder = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'frontend'))
    app = Flask(__name__, static_folder=frontend_folder, static_url_path='')
    app.config.from_object(Config)

    # Aplica cabeceras HTTP de seguridad y lista blanca de orígenes CORS
    @app.after_request
    def apply_security_and_cors_headers(response):
        origin = request.headers.get('Origin')
        if origin and origin in app.config['ALLOWED_ORIGINS']:
            response.headers['Access-Control-Allow-Origin'] = origin
            response.headers['Access-Control-Allow-Credentials'] = 'true'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'

        # Cabeceras de endurecimiento contra Clickjacking y MIME Sniffing (OWASP A05)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        return response

    # Manejadores globales de excepciones con reversión de transacción automática (Rollback)
    @app.errorhandler(ValueError)
    def handle_value_error(err):
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(err)}), 400

    @app.errorhandler(SQLAlchemyError)
    def handle_database_error(err):
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error de integridad o consulta en la base de datos'
        }), 500

    @app.errorhandler(404)
    def handle_not_found(err):
        if request.path.startswith('/api/'):
            return jsonify({'status': 'error', 'message': 'El recurso solicitado no existe'}), 404
        return err

    @app.errorhandler(Exception)
    def handle_unexpected_exception(err):
        if isinstance(err, HTTPException):
            if request.path.startswith('/api/'):
                return jsonify({'status': 'error', 'message': err.description}), err.code
            return err
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'Error interno del servidor'}), 500

    # Vincula SQLAlchemy con la aplicación Flask
    db.init_app(app)

    # Registra todos los módulos de rutas (Login, Búsqueda, Movimientos y Mantenimientos)
    app.register_blueprint(auth_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(movement_bp)
    app.register_blueprint(maintenance_bp)

    # Ruta raíz para servir la interfaz web directamente desde el mismo servidor
    @app.route('/')
    def serve_index():
        """Sirve la página principal del sistema si existe en la carpeta frontend."""
        index_path = os.path.join(frontend_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(frontend_folder, 'index.html')
        return {'status': 'running', 'message': 'API Backend Inmuebles PY activa'}, 200

    # Crea las 10 tablas e inserta los datos iniciales automáticamente si la BD está vacía
    with app.app_context():
        db.create_all()
        inicializar_datos_semilla()

    return app
