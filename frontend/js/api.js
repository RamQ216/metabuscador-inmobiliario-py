// =============================================================================
// CLIENTE HTTP API (frontend/js/api.js)
// Gestiona las peticiones hacia el backend Flask y el Keep-Alive automático
// =============================================================================

// Detecta automáticamente si se ejecuta en local o en producción (Render)
// Usando '/api/v1' relativo, el navegador siempre consulta al mismo dominio que sirve la web
const API_BASE_URL = window.location.origin.includes('file:')
    ? 'http://127.0.0.1:5000/api/v1'
    : `${window.location.origin}/api/v1`;

/**
 * Función auxiliar genérica para realizar llamadas HTTP con soporte de sesión.
 */
async function requestJson(endpoint, options = {}) {
    const config = {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        ...options
    };
    const response = await fetch(`${API_BASE_URL}${endpoint}`, config);
    const data = await response.json();
    if (!response.ok) {
        throw new Error(data.message || 'Error en la comunicación con el servidor');
    }
    return data;
}

/**
 * Envía un ping periódico cada 14 minutos al backend para evitar el Cold Start en Render.
 */
export function iniciarKeepAlive() {
    const ping = () => fetch(`${API_BASE_URL}/health`).catch(() => null);
    ping();
    setInterval(ping, 14 * 60 * 1000);
}

// -----------------------------------------------------------------------------
// 1. AUTENTICACIÓN Y SESIÓN (Requisito 8.2)
// -----------------------------------------------------------------------------

/** Inicia sesión con email y contraseña. */
export async function loginUsuario(email, password) {
    return await requestJson('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
    });
}

/** Cierra la sesión activa del usuario. */
export async function logoutUsuario() {
    return await requestJson('/auth/logout', { method: 'POST' });
}

/** Consulta si hay un usuario autenticado actualmente. */
export async function obtenerSesionActual() {
    return await requestJson('/auth/me');
}

/** Registra una nueva cuenta de usuario con rol Cliente. */
export async function registrarUsuario(datos) {
    return await requestJson('/auth/register', {
        method: 'POST',
        body: JSON.stringify(datos)
    });
}

// -----------------------------------------------------------------------------
// 2. CATÁLOGOS, BÚSQUEDA Y COMPARACIÓN CRUZADA
// -----------------------------------------------------------------------------

/** Obtiene ciudades, barrios, tipos de inmueble y agencias para los filtros. */
export async function obtenerCatalogos() {
    return await requestJson('/catalogs');
}

/** Consulta propiedades agrupadas aplicando filtros de búsqueda en Guaraníes. */
export async function buscarPropiedades(filtros = {}) {
    const params = new URLSearchParams();
    Object.entries(filtros).forEach(([key, val]) => {
        if (val !== undefined && val !== null && val !== '') {
            params.append(key, val);
        }
    });
    return await requestJson(`/properties/search?${params.toString()}`);
}

/** Obtiene el detalle comparativo lado a lado de un inmueble específico. */
export async function obtenerComparativaInmueble(inmuebleId) {
    return await requestJson(`/properties/${inmuebleId}/compare`);
}

/** Obtiene el valor promedio por metro cuadrado (Gs./m2) por barrio. */
export async function obtenerPrecioM2PorBarrio(operacion = 'alquiler') {
    return await requestJson(`/analytics/price-per-m2?operacion=${operacion}`);
}

// -----------------------------------------------------------------------------
// 3. MOVIMIENTOS TRANSACCIONALES: SOLICITUDES DE VISITA (Requisito 8.1)
// -----------------------------------------------------------------------------

/** Lista las solicitudes de visita registradas (Cabecera y Detalle). */
export async function listarSolicitudesVisita(usuarioId = null) {
    const query = usuarioId ? `?usuario_id=${usuarioId}` : '';
    return await requestJson(`/movements/visits${query}`);
}

/** Crea una nueva Solicitud de Visita Comparada congelando precios por agencia. */
export async function crearSolicitudVisita(payload) {
    return await requestJson('/movements/visits', {
        method: 'POST',
        body: JSON.stringify(payload)
    });
}

/** Cambia el estado de una solicitud (PENDIENTE, CONFIRMADA, REALIZADA, CANCELADA). */
export async function actualizarEstadoSolicitud(solicitudId, estado) {
    return await requestJson(`/movements/visits/${solicitudId}/status`, {
        method: 'PUT',
        body: JSON.stringify({ estado })
    });
}

/** Elimina una solicitud de visita registrada. */
export async function eliminarSolicitudVisita(solicitudId) {
    return await requestJson(`/movements/visits/${solicitudId}`, {
        method: 'DELETE'
    });
}

// -----------------------------------------------------------------------------
// 4. MANTENIMIENTOS DEL SISTEMA / CRUDs (Requisito 8.4)
// -----------------------------------------------------------------------------

/** Ejecuta operación CRUD genérica sobre cualquier entidad de mantenimiento. */
export async function crudMantenimiento(recurso, metodo = 'GET', body = null, id = null) {
    const url = id ? `/maintenance/${recurso}/${id}` : `/maintenance/${recurso}`;
    const opts = { method: metodo };
    if (body) opts.body = JSON.stringify(body);
    return await requestJson(url, opts);
}

/** Dispara manualmente el pipeline de scraping y deduplicación por puntaje. */
export async function ejecutarScraperEnVivo() {
    return await requestJson('/maintenance/run-scraper', { method: 'POST' });
}
