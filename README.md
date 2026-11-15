# Metabuscador y Comparador Cruzado Inmobiliario (Paraguay)

Sistema de información web y motor de comparación cruzada para el mercado inmobiliario de **Asunción y Gran Asunción**, diseñado bajo una arquitectura de costo **$0 USD** y cumpliendo estrictamente con los requisitos académicos de Ingeniería / Análisis de Sistemas:

- **Base de Datos Normalizada hasta la 3ra Forma Normal (3FN)** con **10 tablas relacionadas** ([`database/schema.sql`](database/schema.sql)).
- **Moneda 100% unificada en Guaraníes (`PYG`)**.
- **Motor de Deduplicación por Puntaje Acumulado (Scoring 0–100 pts)** para agrupar casas y departamentos publicados simultáneamente en **RE/MAX Paraguay** e **InfoCasas Paraguay**.
- **Georreferenciación con Leaflet.js + `Leaflet.markercluster`** por centroides de barrio.
- **Módulos Académicos Completos:**
  - **Requisito 8.1 (Movimiento Transaccional):** Solicitud de Visita Comparada con Cabecera (`solicitudes_visita`) y Detalle (`solicitud_detalles`) congelando precios y expensas.
  - **Requisito 8.2 (Login):** Control de acceso por roles (*Administrador* y *Cliente*).
  - **Requisito 8.3 (Menú Principal):** Navegación estructurada en 4 módulos.
  - **Requisito 8.4 (Mantenimientos):** CRUDs completos de Agencias, Barrios, Ciudades, Tipos de Inmueble y Usuarios.
  - **Requisito 7 (Manual de Usuario):** Incluido en [`MANUAL_DE_USUARIO.md`](MANUAL_DE_USUARIO.md).

---

## Ejecución Rápida en Local (Evaluación Docente en 1 Clic)

El sistema cuenta con **autoinicialización**: si no se configura una variable `DATABASE_URL` externa de PostgreSQL/Supabase, crea automáticamente la base de datos local con las **10 tablas en 3FN** y carga los datos semilla de Paraguay ([`backend/app/services/seeder.py`](backend/app/services/seeder.py)).

```bash
# 1. Entrar a la carpeta backend e instalar dependencias
cd backend
pip install -r requirements.txt

# 2. Iniciar el servidor (sirve tanto la API como el Frontend en http://127.0.0.1:5000)
python wsgi.py
```

Luego abrir en el navegador: **`http://127.0.0.1:5000`**

### Credenciales de Prueba:
- **Administrador:** `admin@inmueblespy.com` / `admin123`
- **Cliente:** `maria@gmail.com` / `cliente123`
