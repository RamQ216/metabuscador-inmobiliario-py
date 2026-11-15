import os
from app import create_app

# Instancia principal de la aplicación Flask para desarrollo o Gunicorn (Render)
app = create_app()

if __name__ == '__main__':
    # Activa modo debug únicamente si se indica explícitamente en variable de entorno
    modo_debug = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'
    puerto = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=puerto, debug=modo_debug)
