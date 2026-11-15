// =============================================================================
// CONTROLADOR PRINCIPAL DEL FRONTEND (frontend/js/main.js)
// Incluye sanitización anti-XSS (escapeHtml), Control de Acceso Basado en Roles (RBAC),
// Registro de Cuenta, Movimientos (8.1) y Mantenimientos CRUD con Edición (8.4)
// =============================================================================

import {
    iniciarKeepAlive,
    loginUsuario,
    logoutUsuario,
    obtenerSesionActual,
    registrarUsuario,
    obtenerCatalogos,
    buscarPropiedades,
    obtenerComparativaInmueble,
    obtenerPrecioM2PorBarrio,
    listarSolicitudesVisita,
    crearSolicitudVisita,
    actualizarEstadoSolicitud,
    eliminarSolicitudVisita,
    crudMantenimiento,
    ejecutarScraperEnVivo
} from './api.js';

import {
    inicializarMapa,
    actualizarMarcadoresMapa,
    enfocarPropiedadEnMapa
} from './map.js';

// Estado global de la sesión y catálogos en el cliente
const state = {
    currentUser: null,
    catalogs: { ciudades: [], barrios: [], tipos_inmueble: [], agencias: [] },
    properties: [],
    selectedPropertyId: 1,
    activeMaintTab: 'agencies',
    activeView: 'explorador'
};

/**
 * Escapa caracteres especiales HTML (<, >, &, ", ') para prevenir ataques XSS (OWASP A03).
 */
function escapeHtml(valor) {
    if (valor === null || valor === undefined) return '';
    return String(valor)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/**
 * Formatea números a moneda local Guaraníes (Ej: Gs. 6.180.000).
 */
function formatPyg(monto) {
    return `Gs. ${Number(monto || 0).toLocaleString('es-PY')}`;
}

/**
 * Muestra un aviso breve en la esquina inferior derecha para confirmar acciones.
 */
function mostrarNotificacion(mensaje) {
    const banner = document.getElementById('toast-banner');
    if (!banner) return;
    banner.textContent = mensaje;
    banner.classList.remove('hidden');
    setTimeout(() => banner.classList.add('hidden'), 4200);
}

// =============================================================================
// 1. NAVEGACIÓN DEL MENÚ PRINCIPAL Y CONTROL DE ROL (Requisitos 8.3 y 8.4)
// =============================================================================

/**
 * Cambia entre las 4 vistas principales validando permisos de rol para Mantenimientos.
 */
export async function cambiarVistaMenu(vistaDestino, propId = null) {
    // Si no es Administrador, nunca puede abrir la vista de Mantenimientos
    const esAdmin = Boolean(state.currentUser && state.currentUser.rol_nombre === 'Administrador');
    if (vistaDestino === 'mantenimientos' && !esAdmin) {
        vistaDestino = 'explorador';
    }

    state.activeView = vistaDestino;
    const vistas = ['explorador', 'comparador', 'movimientos', 'mantenimientos'];
    vistas.forEach((v) => {
        const sec = document.getElementById(`view-${v}`);
        if (sec) sec.classList.toggle('hidden', v !== vistaDestino);
    });

    // Actualiza estilo visual del tab activo respetando que Mantenimientos esté oculto si no es Admin
    document.querySelectorAll('.nav-tab').forEach((btn) => {
        const navKey = btn.getAttribute('data-nav');
        if (navKey === 'mantenimientos' && !esAdmin) {
            btn.classList.add('hidden');
            return;
        }
        const esActivo = navKey === vistaDestino;
        btn.className = esActivo
            ? 'nav-tab tactile-btn px-3 py-1.5 text-xs sm:text-sm font-medium rounded border border-[#121316] bg-[#121316] text-[#FBFBF9]'
            : 'nav-tab tactile-btn px-3 py-1.5 text-xs sm:text-sm font-medium rounded border border-transparent text-[#52555A] hover:text-[#121316] hover:border-[#E4E4DF]';
    });

    if (vistaDestino === 'explorador') {
        inicializarMapa('leaflet-map');
    } else if (vistaDestino === 'comparador') {
        const idAInspeccionar = propId || state.selectedPropertyId || 1;
        await cargarVistaComparativa(idAInspeccionar);
    } else if (vistaDestino === 'movimientos') {
        await renderizarModuloMovimientos();
    } else if (vistaDestino === 'mantenimientos') {
        await renderizarModuloMantenimiento(state.activeMaintTab);
    }
}

// =============================================================================
// 2. GESTIÓN DE LOGIN, REGISTRO Y SESIÓN (Requisito 8.2)
// =============================================================================

/**
 * Actualiza los botones de la barra superior y oculta Mantenimientos si no es Administrador.
 */
function actualizarInterfazSesion() {
    const badge = document.getElementById('user-session-badge');
    const nameLabel = document.getElementById('user-display-name');
    const btnOpenAuth = document.getElementById('btn-open-auth');
    const btnLogout = document.getElementById('btn-logout');
    const btnMaint = document.getElementById('nav-btn-mantenimientos');
    const secMaint = document.getElementById('view-mantenimientos');

    const esAdmin = Boolean(state.currentUser && state.currentUser.rol_nombre === 'Administrador');

    if (state.currentUser) {
        badge.classList.remove('hidden');
        badge.classList.add('flex');
        nameLabel.textContent = `${state.currentUser.nombre} (${state.currentUser.rol_nombre})`;
        btnOpenAuth.classList.add('hidden');
        btnLogout.classList.remove('hidden');
    } else {
        badge.classList.add('hidden');
        btnOpenAuth.classList.remove('hidden');
        btnLogout.classList.add('hidden');
    }

    // Muestra la opción 04 Mantenimientos (ABM) exclusivamente al rol Administrador
    if (btnMaint) {
        btnMaint.classList.toggle('hidden', !esAdmin);
    }

    // Si estaba en la ventana de Mantenimientos y pasó a Invitado o Cliente, oculta la ventana y vuelve al explorador
    if (!esAdmin) {
        if (secMaint) secMaint.classList.add('hidden');
        if (state.activeView === 'mantenimientos') {
            cambiarVistaMenu('explorador');
        }
    }
}

/**
 * Configura los eventos del modal de Login, Registro de Cuenta y botones rápidos.
 */
function configurarEventosLogin() {
    const modal = document.getElementById('auth-modal');
    const btnOpen = document.getElementById('btn-open-auth');
    const btnClose = document.getElementById('btn-close-auth');
    const btnLogout = document.getElementById('btn-logout');
    const loginForm = document.getElementById('login-form');
    const registerForm = document.getElementById('register-form');
    const panelLogin = document.getElementById('panel-auth-login');
    const tabLogin = document.getElementById('tab-auth-login');
    const tabRegister = document.getElementById('tab-auth-register');
    const loginError = document.getElementById('login-error-msg');
    const regError = document.getElementById('register-error-msg');

    btnOpen.addEventListener('click', () => modal.classList.remove('hidden'));
    btnClose.addEventListener('click', () => modal.classList.add('hidden'));

    // Alternancia entre pestaña Iniciar Sesión y Crear Cuenta
    tabLogin.addEventListener('click', () => {
        panelLogin.classList.remove('hidden');
        registerForm.classList.add('hidden');
        tabLogin.className = 'py-1.5 rounded bg-[#121316] text-[#FBFBF9]';
        tabRegister.className = 'py-1.5 rounded text-[#52555A] hover:text-[#121316]';
    });

    tabRegister.addEventListener('click', () => {
        panelLogin.classList.add('hidden');
        registerForm.classList.remove('hidden');
        tabRegister.className = 'py-1.5 rounded bg-[#121316] text-[#FBFBF9]';
        tabLogin.className = 'py-1.5 rounded text-[#52555A] hover:text-[#121316]';
    });

    // Botones de 1 clic para facilitar evaluación del profesor
    document.getElementById('btn-quick-admin').addEventListener('click', () => {
        document.getElementById('login-email').value = 'admin@inmueblespy.com';
        document.getElementById('login-password').value = 'admin123';
    });

    document.getElementById('btn-quick-client').addEventListener('click', () => {
        document.getElementById('login-email').value = 'maria@gmail.com';
        document.getElementById('login-password').value = 'cliente123';
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        loginError.classList.add('hidden');
        const email = document.getElementById('login-email').value;
        const pass = document.getElementById('login-password').value;

        try {
            const res = await loginUsuario(email, pass);
            state.currentUser = res.user;
            actualizarInterfazSesion();
            modal.classList.add('hidden');
            mostrarNotificacion(`Sesión iniciada: ${res.user.nombre_completo} [${res.user.rol_nombre}]`);
        } catch (err) {
            loginError.textContent = err.message;
            loginError.classList.remove('hidden');
        }
    });

    registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        regError.classList.add('hidden');
        try {
            const res = await registrarUsuario({
                nombre: document.getElementById('reg-nombre').value,
                apellido: document.getElementById('reg-apellido').value,
                email: document.getElementById('reg-email').value,
                telefono: document.getElementById('reg-telefono').value,
                password: document.getElementById('reg-password').value
            });
            state.currentUser = res.user;
            actualizarInterfazSesion();
            modal.classList.add('hidden');
            registerForm.reset();
            mostrarNotificacion(`Cuenta creada y sesión activa: ${res.user.nombre_completo}`);
        } catch (err) {
            regError.textContent = err.message;
            regError.classList.remove('hidden');
        }
    });

    btnLogout.addEventListener('click', async () => {
        await logoutUsuario();
        state.currentUser = null;
        actualizarInterfazSesion();
        mostrarNotificacion('Sesión finalizada correctamente');
    });
}

// =============================================================================
// 3. EXPLORADOR DE PROPIEDADES Y FILTROS (Vista 01)
// =============================================================================

/**
 * Carga las opciones de Ciudades, Barrios y Tipos de Inmueble en los selectores sanitizando HTML.
 */
function poblarSelectoresCatalogos() {
    const selCiudad = document.getElementById('filter-ciudad');
    const selBarrio = document.getElementById('filter-barrio');
    const selTipo = document.getElementById('filter-tipo');

    selCiudad.innerHTML = '<option value="">Gran Asunción (Todas)</option>' +
        state.catalogs.ciudades.map((c) => `<option value="${Number(c.id)}">${escapeHtml(c.nombre)}</option>`).join('');

    const renderBarrios = (ciudadId = '') => {
        const filtrados = ciudadId
            ? state.catalogs.barrios.filter((b) => String(b.ciudad_id) === String(ciudadId))
            : state.catalogs.barrios;
        selBarrio.innerHTML = '<option value="">Todos los barrios</option>' +
            filtrados.map((b) => `<option value="${Number(b.id)}">${escapeHtml(b.nombre)} (${escapeHtml(b.ciudad_nombre)})</option>`).join('');
    };

    renderBarrios();
    selCiudad.addEventListener('change', (e) => renderBarrios(e.target.value));

    selTipo.innerHTML = '<option value="">Casa / Dpto / Dúplex</option>' +
        state.catalogs.tipos_inmueble.map((t) => `<option value="${Number(t.id)}">${escapeHtml(t.nombre)}</option>`).join('');
}

/**
 * Renderiza el listado editorial de propiedades sanitizando textos dinámicos contra XSS.
 */
function renderizarListaPropiedades(propiedades) {
    const container = document.getElementById('properties-list-container');
    const counterLabel = document.getElementById('results-counter-label');
    const statTotal = document.getElementById('stat-total-inmuebles');
    const statDup = document.getElementById('stat-total-duplicados');

    const totalDuplicados = propiedades.filter((p) => p.es_duplicado).length;
    statTotal.textContent = propiedades.length;
    statDup.textContent = totalDuplicados;
    counterLabel.textContent = `${propiedades.length} inmuebles físicos encontrados (${totalDuplicados} publicados en múltiples agencias)`;

    if (propiedades.length === 0) {
        container.innerHTML = `
            <div class="p-10 text-center text-sm text-[#52555A]">
                No se encontraron propiedades con los filtros seleccionados.
            </div>
        `;
        return;
    }

    container.innerHTML = propiedades.map((item) => {
        const badgeCruce = item.es_duplicado
            ? `<span class="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-mono-tech font-medium bg-[#EBF2EE] text-[#2E5A44] border border-[#C5D9CD]">
                 ● Publicado en ${Number(item.cantidad_agencias)} agencias · Diferencia: ${formatPyg(item.diferencia_pyg)}
               </span>`
            : `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-[11px] font-mono-tech bg-[#F4F4F0] text-[#52555A] border border-[#E4E4DF]">
                 1 agencia (${escapeHtml(item.publicaciones[0]?.agencia_nombre || 'Verificada')})
               </span>`;

        const bloquePrecio = item.es_duplicado
            ? `<div class="font-mono-tech text-xs text-[#52555A]">Desde</div>
               <div class="font-mono-tech text-lg font-semibold text-[#121316]">${formatPyg(item.precio_min_pyg)}</div>
               <div class="font-mono-tech text-[11px] text-[#82868C]">Hasta ${formatPyg(item.precio_max_pyg)}</div>`
            : `<div class="font-mono-tech text-xs text-[#52555A]">Precio publicado</div>
               <div class="font-mono-tech text-lg font-semibold text-[#121316]">${formatPyg(item.precio_min_pyg)}</div>`;

        const imgUrl = escapeHtml(item.imagen_principal || 'https://images.unsplash.com/photo-1560448204-e02f11c3d0e2?auto=format&fit=crop&w=600&q=80');

        return `
            <article class="p-5 hover:bg-[#FBFBF9] transition-colors flex flex-col sm:flex-row gap-5 justify-between">
                <div class="flex gap-4 flex-1">
                    <img src="${imgUrl}"
                         alt="${escapeHtml(item.titulo_canonico)}"
                         class="w-28 h-28 sm:w-36 sm:h-28 object-cover rounded border border-[#E4E4DF] shrink-0 bg-[#F4F4F0]" />
                    <div class="space-y-1.5 flex-1">
                        <div class="flex flex-wrap items-center gap-2">
                            <span class="font-mono-tech text-[11px] uppercase tracking-wider text-[#52555A]">
                                ${escapeHtml(item.ciudad)} · ${escapeHtml(item.barrio)} · ${escapeHtml(item.tipo_operacion.toUpperCase())}
                            </span>
                            ${badgeCruce}
                        </div>
                        <h2 class="font-semibold text-base text-[#121316] leading-snug">
                            ${escapeHtml(item.titulo_canonico)}
                        </h2>
                        <div class="flex flex-wrap items-center gap-3 text-xs font-mono-tech text-[#52555A] pt-1">
                            <span>${escapeHtml(item.tipo_inmueble)}</span>
                            <span>·</span>
                            <span>${Number(item.superficie_m2)} m²</span>
                            <span>·</span>
                            <span>${Number(item.dormitorios)} dorm.</span>
                            <span>·</span>
                            <span>${Number(item.banos)} baño(s)</span>
                        </div>
                    </div>
                </div>

                <div class="flex sm:flex-col justify-between items-end sm:text-right border-t sm:border-t-0 pt-3 sm:pt-0 border-[#E4E4DF] shrink-0">
                    <div>${bloquePrecio}</div>
                    <div class="flex items-center gap-2 mt-2">
                        <button type="button" data-focus-lat="${Number(item.latitud)}" data-focus-lon="${Number(item.longitud)}"
                                class="btn-locate-map tactile-btn px-2.5 py-1.5 text-xs font-mono-tech text-[#52555A] bg-[#F4F4F0] hover:text-[#121316] border border-[#D4D4CC] rounded">
                            Mapa
                        </button>
                        <button type="button" data-compare-id="${Number(item.id)}"
                                class="btn-open-compare tactile-btn px-3.5 py-1.5 text-xs font-medium bg-[#121316] text-[#FBFBF9] hover:bg-[#272930] rounded">
                            ${item.es_duplicado ? 'Comparar ofertas →' : 'Ver ficha →'}
                        </button>
                    </div>
                </div>
            </article>
        `;
    }).join('');

    container.querySelectorAll('.btn-locate-map').forEach((btn) => {
        btn.addEventListener('click', () => {
            enfocarPropiedadEnMapa(
                parseFloat(btn.getAttribute('data-focus-lat')),
                parseFloat(btn.getAttribute('data-focus-lon'))
            );
        });
    });

    container.querySelectorAll('.btn-open-compare').forEach((btn) => {
        btn.addEventListener('click', () => {
            const propId = parseInt(btn.getAttribute('data-compare-id'), 10);
            state.selectedPropertyId = propId;
            cambiarVistaMenu('comparador', propId);
        });
    });
}

/**
 * Ejecuta la consulta de propiedades con los filtros activos y sincroniza el mapa Leaflet.
 */
async function ejecutarBusquedaFiltrada() {
    const filtros = {
        operacion: document.getElementById('filter-operacion').value,
        ciudad_id: document.getElementById('filter-ciudad').value,
        barrio_id: document.getElementById('filter-barrio').value,
        tipo_inmueble_id: document.getElementById('filter-tipo').value,
        dormitorios: document.getElementById('filter-dormitorios').value,
        max_price: document.getElementById('filter-max-price').value,
        solo_duplicados: document.getElementById('filter-solo-duplicados').checked ? 'true' : ''
    };

    const res = await buscarPropiedades(filtros);
    state.properties = res.data || [];
    renderizarListaPropiedades(state.properties);
    actualizarMarcadoresMapa(state.properties, (idSeleccionado) => {
        state.selectedPropertyId = idSeleccionado;
        cambiarVistaMenu('comparador', idSeleccionado);
    });
}

/**
 * Carga la tabla de valores referenciales por metro cuadrado (Gs./m2) por barrio.
 */
async function cargarAnaliticaM2() {
    const box = document.getElementById('analytics-m2-container');
    try {
        const res = await obtenerPrecioM2PorBarrio('alquiler');
        const items = res.data || [];
        box.innerHTML = items.map((row) => `
            <div class="py-1.5 flex items-center justify-between">
                <span class="text-[#121316]">${escapeHtml(row.barrio)} <span class="text-[#82868C]">(${escapeHtml(row.ciudad)})</span></span>
                <span class="font-semibold text-[#2E5A44]">${formatPyg(row.promedio_gs_m2)} / m²</span>
            </div>
        `).join('');
    } catch (_) {
        box.innerHTML = '<div class="py-2 text-[#82868C]">Sin datos de referencia.</div>';
    }
}

// =============================================================================
// 4. VISTA DE COMPARACIÓN CRUZADA LADO A LADO (Vista 02)
// =============================================================================

/**
 * Renderiza la comparativa lado a lado (Precio, Expensas y Superficie) sanitizada contra XSS.
 */
async function cargarVistaComparativa(inmuebleId) {
    const container = document.getElementById('compare-detail-container');
    container.innerHTML = '<div class="py-8 text-center font-mono-tech text-xs text-[#52555A]">Cargando comparativa cruzada...</div>';

    try {
        const res = await obtenerComparativaInmueble(inmuebleId);
        const prop = res.data;
        state.selectedPropertyId = prop.id;

        const minPrecio = prop.precio_min_pyg;
        const hoyMas2 = new Date(Date.now() + 2 * 86400000).toISOString().split('T')[0];

        const columnasAgencias = prop.publicaciones.map((pub, idx) => {
            const esMasBarata = Number(pub.precio_pyg) === Number(minPrecio) && prop.publicaciones.length > 1;
            const badgeMejor = esMasBarata
                ? `<span class="px-2 py-0.5 text-[11px] font-mono-tech bg-[#2E5A44] text-white rounded">MEJOR OFERTA DETECTADA</span>`
                : `<span class="px-2 py-0.5 text-[11px] font-mono-tech bg-[#F4F4F0] text-[#52555A] rounded">OFERTA #${idx + 1}</span>`;

            return `
                <div class="p-5 border ${esMasBarata ? 'border-[#2E5A44] bg-[#FBFDFB]' : 'border-[#E4E4DF] bg-white'} rounded flex flex-col justify-between space-y-4">
                    <div class="space-y-3">
                        <div class="flex items-center justify-between border-b border-[#E4E4DF] pb-3">
                            <div>
                                <span class="block text-xs font-mono-tech uppercase text-[#52555A]">Inmobiliaria Fuente</span>
                                <strong class="text-base text-[#121316]">${escapeHtml(pub.agencia_nombre)}</strong>
                            </div>
                            ${badgeMejor}
                        </div>

                        <p class="text-xs font-medium text-[#121316]">${escapeHtml(pub.titulo_original)}</p>
                        <p class="text-xs text-[#52555A] leading-relaxed">${escapeHtml(pub.descripcion || 'Sin observaciones adicionales.')}</p>

                        <div class="divide-y divide-[#E4E4DF] border-t border-b border-[#E4E4DF] font-mono-tech text-xs">
                            <div class="py-2.5 flex justify-between items-center">
                                <span class="text-[#52555A]">1. Precio Normalizado (PYG):</span>
                                <strong class="text-sm ${esMasBarata ? 'text-[#2E5A44]' : 'text-[#121316]'}">${formatPyg(pub.precio_pyg)}</strong>
                            </div>
                            <div class="py-2.5 flex justify-between items-center">
                                <span class="text-[#52555A]">2. Expensas Reportadas:</span>
                                <strong class="text-[#121316]">${pub.expensas_pyg > 0 ? formatPyg(pub.expensas_pyg) : 'Gs. 0 (Incluidas)'}</strong>
                            </div>
                            <div class="py-2.5 flex justify-between items-center bg-[#F4F4F0]/60 px-2">
                                <span class="text-[#121316] font-semibold">Costo Mensual Real (Precio + Exp.):</span>
                                <strong class="text-sm text-[#121316]">${formatPyg(pub.costo_total_mensual_pyg)}</strong>
                            </div>
                            <div class="py-2.5 flex justify-between items-center">
                                <span class="text-[#52555A]">3. Superficie según agencia:</span>
                                <strong class="text-[#121316]">${Number(pub.superficie_reportada_m2)} m²</strong>
                            </div>
                        </div>
                    </div>

                    <div class="pt-2 flex items-center justify-between gap-3">
                        <span class="text-[11px] font-mono-tech text-[#82868C]">Tel: ${escapeHtml(pub.agencia_telefono || 'N/D')}</span>
                        <a href="${escapeHtml(pub.url_externa)}" target="_blank" rel="noopener noreferrer"
                           class="tactile-btn px-3 py-1.5 text-xs font-mono-tech border border-[#121316] text-[#121316] hover:bg-[#121316] hover:text-white rounded">
                            Abrir aviso original ↗
                        </a>
                    </div>
                </div>
            `;
        }).join('');

        const checkboxesAgencias = prop.publicaciones.map((pub) => `
            <label class="flex items-center justify-between p-2.5 bg-white border border-[#D4D4CC] rounded text-xs cursor-pointer">
                <span class="flex items-center gap-2">
                    <input type="checkbox" name="publicacion_ids" value="${Number(pub.id)}" checked class="accent-[#2E5A44] w-4 h-4" />
                    <strong>${escapeHtml(pub.agencia_nombre)}</strong>
                </span>
                <span class="font-mono-tech text-[#2E5A44]">
                    Congelar: ${formatPyg(pub.precio_pyg)} + Exp. ${formatPyg(pub.expensas_pyg)}
                </span>
            </label>
        `).join('');

        container.innerHTML = `
            <div class="border-b border-[#E4E4DF] pb-5 flex flex-col lg:flex-row lg:items-end justify-between gap-4">
                <div>
                    <div class="flex items-center gap-2 font-mono-tech text-xs text-[#2E5A44] uppercase">
                        <span>PROPIEDAD FÍSICA #${Number(prop.id)}</span>
                        <span>·</span>
                        <span>${escapeHtml(prop.ciudad)} / ${escapeHtml(prop.barrio)}</span>
                        <span>·</span>
                        <span>VALOR M²: ${formatPyg(prop.precio_m2_min_pyg)}/m²</span>
                    </div>
                    <h2 class="font-editorial text-3xl sm:text-4xl text-[#121316] mt-1">${escapeHtml(prop.titulo_canonico)}</h2>
                    <p class="text-xs font-mono-tech text-[#52555A] mt-1">
                        Superficie canónica: ${Number(prop.superficie_m2)} m² · ${Number(prop.dormitorios)} Dormitorios · ${Number(prop.banos)} Baños · ${Number(prop.estacionamientos)} Cochera(s)
                    </p>
                </div>
                <div class="p-3 bg-[#EBF2EE] border border-[#C5D9CD] rounded text-right font-mono-tech">
                    <span class="block text-[11px] uppercase text-[#2E5A44]">Diferencia Máxima entre Inmobiliarias</span>
                    <strong class="text-xl text-[#2E5A44]">${formatPyg(prop.diferencia_pyg)}</strong>
                </div>
            </div>

            <div class="mt-6">
                <h3 class="text-xs font-mono-tech uppercase tracking-wider text-[#52555A] mb-3">
                    Comparativa Cruzada de Publicaciones Activas (${prop.publicaciones.length})
                </h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
                    ${columnasAgencias}
                </div>
            </div>

            <div class="mt-8 p-5 bg-[#F4F4F0] border border-[#D4D4CC] rounded">
                <div class="mb-3">
                    <span class="font-mono-tech text-[11px] uppercase text-[#2E5A44]">OPERACIÓN TRANSACCIONAL · REQUISITO 8.1</span>
                    <h3 class="font-editorial text-2xl text-[#121316]">Generar Solicitud de Visita Comparada</h3>
                    <p class="text-xs text-[#52555A]">
                        Seleccione las agencias que desea incluir en el detalle de su solicitud. El sistema congelará los precios vigentes de cada una.
                    </p>
                </div>

                <form id="form-create-movement" class="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
                    <div class="md:col-span-5 space-y-2">
                        <label class="block font-mono-tech text-xs text-[#52555A]">Agencias a incluir en el Detalle:</label>
                        ${checkboxesAgencias}
                    </div>
                    <div class="md:col-span-3">
                        <label class="block font-mono-tech text-xs text-[#52555A] mb-1">Fecha de Visita Propuesta</label>
                        <input type="date" id="mov-fecha" value="${hoyMas2}" required class="w-full px-3 py-2 text-xs font-mono-tech bg-white border border-[#D4D4CC] rounded" />
                        <label class="block font-mono-tech text-xs text-[#52555A] mt-2 mb-1">Franja Horaria</label>
                        <select id="mov-horario" class="w-full px-3 py-2 text-xs bg-white border border-[#D4D4CC] rounded">
                            <option value="Mañana (09:00 - 12:00)">Mañana (09:00 - 12:00)</option>
                            <option value="Siesta (13:00 - 15:00)">Siesta (13:00 - 15:00)</option>
                            <option value="Tarde (15:30 - 18:30)">Tarde (15:30 - 18:30)</option>
                        </select>
                    </div>
                    <div class="md:col-span-4 space-y-2">
                        <label class="block font-mono-tech text-xs text-[#52555A]">Observaciones para las agencias</label>
                        <textarea id="mov-obs" rows="2" placeholder="Ej: Deseo confirmar si el precio incluye IVA y expensas." class="w-full px-3 py-2 text-xs bg-white border border-[#D4D4CC] rounded"></textarea>
                        <button type="submit" class="tactile-btn w-full py-2.5 px-4 bg-[#121316] text-white text-xs font-mono-tech uppercase tracking-wider rounded hover:bg-[#272930]">
                            Registrar Movimiento de Visita
                        </button>
                    </div>
                </form>
            </div>
        `;

        document.getElementById('form-create-movement').addEventListener('submit', async (e) => {
            e.preventDefault();
            if (!state.currentUser) {
                document.getElementById('auth-modal').classList.remove('hidden');
                mostrarNotificacion('Inicie sesión primero para registrar el movimiento');
                return;
            }

            const seleccionados = Array.from(
                container.querySelectorAll('input[name="publicacion_ids"]:checked')
            ).map((el) => parseInt(el.value, 10));

            try {
                await crearSolicitudVisita({
                    inmueble_id: prop.id,
                    publicacion_ids: seleccionados,
                    fecha_visita_propuesta: document.getElementById('mov-fecha').value,
                    horario_preferido: document.getElementById('mov-horario').value,
                    observaciones: document.getElementById('mov-obs').value
                });
                mostrarNotificacion('Movimiento registrado con éxito (Cabecera + Detalle)');
                cambiarVistaMenu('movimientos');
            } catch (err) {
                mostrarNotificacion(`Error: ${err.message}`);
            }
        });
    } catch (err) {
        container.innerHTML = `<div class="p-6 text-xs text-[#B84A27] font-mono-tech">${escapeHtml(err.message)}</div>`;
    }
}

// =============================================================================
// 5. MÓDULO DE MOVIMIENTOS TRANSACCIONALES (Vista 03 - Requisito 8.1)
// =============================================================================

/**
 * Muestra todas las Solicitudes de Visita con su Cabecera y Detalle sanitizando datos.
 */
async function renderizarModuloMovimientos() {
    const container = document.getElementById('movements-list-container');
    container.innerHTML = '<div class="py-8 text-center font-mono-tech text-xs text-[#52555A]">Cargando movimientos registrados...</div>';

    try {
        const res = await listarSolicitudesVisita();
        const movimientos = res.data || [];

        if (movimientos.length === 0) {
            container.innerHTML = '<div class="p-8 bg-white border border-[#E4E4DF] rounded text-center text-xs text-[#52555A]">No hay movimientos registrados aún.</div>';
            return;
        }

        container.innerHTML = movimientos.map((mov) => {
            const filasDetalle = mov.detalles.map((det) => `
                <tr class="border-t border-[#E4E4DF]">
                    <td class="py-2 px-3 font-medium text-[#121316]">${escapeHtml(det.agencia_nombre)}</td>
                    <td class="py-2 px-3 font-mono-tech text-[#2E5A44] font-semibold">${formatPyg(det.precio_congelado_pyg)}</td>
                    <td class="py-2 px-3 font-mono-tech">${formatPyg(det.expensas_congeladas_pyg)}</td>
                    <td class="py-2 px-3 text-[#52555A]">${escapeHtml(det.comentario_agencia || '')}</td>
                </tr>
            `).join('');

            return `
                <div class="bg-white border border-[#E4E4DF] rounded p-5 space-y-4">
                    <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-[#E4E4DF] pb-3">
                        <div>
                            <span class="font-mono-tech text-xs text-[#52555A]">
                                MOVIMIENTO #${Number(mov.id)} · Solicitud: ${escapeHtml(mov.fecha_solicitud)} · Solicitante: <strong>${escapeHtml(mov.usuario_nombre)}</strong>
                            </span>
                            <h3 class="font-semibold text-base text-[#121316] mt-0.5">
                                ${escapeHtml(mov.inmueble_titulo)} (${escapeHtml(mov.barrio)})
                            </h3>
                        </div>
                        <div class="flex items-center gap-2">
                            <span class="px-2.5 py-1 text-xs font-mono-tech font-semibold rounded bg-[#EBF2EE] text-[#2E5A44] border border-[#C5D9CD]">
                                ${escapeHtml(mov.estado)}
                            </span>
                            <select data-mov-status="${Number(mov.id)}" class="px-2 py-1 text-xs font-mono-tech bg-[#F4F4F0] border border-[#D4D4CC] rounded">
                                <option value="PENDIENTE" ${mov.estado === 'PENDIENTE' ? 'selected' : ''}>PENDIENTE</option>
                                <option value="CONFIRMADA" ${mov.estado === 'CONFIRMADA' ? 'selected' : ''}>CONFIRMADA</option>
                                <option value="REALIZADA" ${mov.estado === 'REALIZADA' ? 'selected' : ''}>REALIZADA</option>
                                <option value="CANCELADA" ${mov.estado === 'CANCELADA' ? 'selected' : ''}>CANCELADA</option>
                            </select>
                            <button type="button" data-mov-del="${Number(mov.id)}" class="px-2.5 py-1 text-xs font-mono-tech text-[#B84A27] border border-[#E4E4DF] hover:border-[#B84A27] rounded">
                                Eliminar
                            </button>
                        </div>
                    </div>

                    <div class="text-xs text-[#52555A] flex flex-wrap gap-4 font-mono-tech">
                        <span>Fecha Visita: <strong>${escapeHtml(mov.fecha_visita_propuesta)}</strong></span>
                        <span>Horario: <strong>${escapeHtml(mov.horario_preferido)}</strong></span>
                        <span>Observaciones: ${escapeHtml(mov.observaciones || 'Ninguna')}</span>
                    </div>

                    <div class="overflow-x-auto border border-[#E4E4DF] rounded">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-[#F4F4F0] font-mono-tech text-[11px] uppercase text-[#52555A]">
                                <tr>
                                    <th class="py-2 px-3">Agencia Seleccionada</th>
                                    <th class="py-2 px-3">Precio Congelado (PYG)</th>
                                    <th class="py-2 px-3">Expensas Congeladas</th>
                                    <th class="py-2 px-3">Referencia de Cruce</th>
                                </tr>
                            </thead>
                            <tbody>${filasDetalle}</tbody>
                        </table>
                    </div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('[data-mov-status]').forEach((sel) => {
            sel.addEventListener('change', async (e) => {
                const id = parseInt(sel.getAttribute('data-mov-status'), 10);
                try {
                    await actualizarEstadoSolicitud(id, e.target.value);
                    mostrarNotificacion(`Movimiento #${id} actualizado a ${e.target.value}`);
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
                await renderizarModuloMovimientos();
            });
        });

        container.querySelectorAll('[data-mov-del]').forEach((btn) => {
            btn.addEventListener('click', async () => {
                const id = parseInt(btn.getAttribute('data-mov-del'), 10);
                try {
                    await eliminarSolicitudVisita(id);
                    mostrarNotificacion(`Movimiento #${id} eliminado`);
                    await renderizarModuloMovimientos();
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
            });
        });
    } catch (err) {
        container.innerHTML = `<div class="p-4 text-xs text-[#B84A27]">${escapeHtml(err.message)}</div>`;
    }
}

// =============================================================================
// 6. MÓDULO DE MANTENIMIENTOS DEL SISTEMA / ABMs COMPLETOS (Alta, Baja y Edición)
// =============================================================================

/**
 * Renderiza el CRUD completo (Crear, Leer, Editar y Eliminar) de la entidad seleccionada.
 */
async function renderizarModuloMantenimiento(tab) {
    state.activeMaintTab = tab;
    const container = document.getElementById('maintenance-content-container');

    document.querySelectorAll('.maint-tab').forEach((btn) => {
        const activo = btn.getAttribute('data-maint') === tab;
        btn.className = activo
            ? 'maint-tab tactile-btn px-3 py-1.5 text-xs font-mono-tech rounded bg-[#121316] text-white'
            : 'maint-tab tactile-btn px-3 py-1.5 text-xs font-mono-tech rounded bg-[#F4F4F0] text-[#52555A] border border-[#D4D4CC]';
    });

    try {
        if (tab === 'agencies') {
            const res = await crudMantenimiento('agencies');
            const rows = res.data || [];
            let editId = null;

            container.innerHTML = `
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <form id="form-abm-agency" class="lg:col-span-4 bg-white border border-[#E4E4DF] rounded p-5 space-y-3 h-fit">
                        <h3 id="title-abm-agency" class="font-mono-tech text-xs uppercase text-[#2E5A44] font-semibold">Alta de Agencia Inmobiliaria</h3>
                        <input type="text" id="ag-nombre" required placeholder="Nombre (Ej: Century 21 PY)" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <input type="url" id="ag-web" required placeholder="https://www.c21.com.py" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <input type="text" id="ag-tel" placeholder="Teléfono (Ej: 021-400500)" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <div class="flex gap-2">
                            <button type="submit" id="btn-submit-agency" class="tactile-btn flex-1 py-2 bg-[#121316] text-white text-xs font-mono-tech rounded">Guardar Agencia</button>
                            <button type="button" id="btn-cancel-agency" class="hidden px-3 py-2 bg-[#F4F4F0] text-xs font-mono-tech border border-[#D4D4CC] rounded">Cancelar</button>
                        </div>
                    </form>
                    <div class="lg:col-span-8 bg-white border border-[#E4E4DF] rounded overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-[#F4F4F0] font-mono-tech uppercase text-[11px] text-[#52555A]">
                                <tr><th class="p-3">ID</th><th class="p-3">Nombre</th><th class="p-3">Sitio Web</th><th class="p-3">Teléfono</th><th class="p-3">Acciones ABM</th></tr>
                            </thead>
                            <tbody class="divide-y divide-[#E4E4DF]">
                                ${rows.map((r) => `
                                    <tr>
                                        <td class="p-3 font-mono-tech">${Number(r.id)}</td>
                                        <td class="p-3 font-semibold">${escapeHtml(r.nombre)}</td>
                                        <td class="p-3 font-mono-tech text-[#52555A]">${escapeHtml(r.sitio_web)}</td>
                                        <td class="p-3 font-mono-tech">${escapeHtml(r.telefono_contacto || '-')}</td>
                                        <td class="p-3 space-x-2 font-mono-tech">
                                            <button type="button" data-edit-agency="${Number(r.id)}" class="text-[#2E5A44] hover:underline">Editar</button>
                                            <button type="button" data-del-agency="${Number(r.id)}" class="text-[#B84A27] hover:underline">Eliminar</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            const btnCancel = document.getElementById('btn-cancel-agency');
            btnCancel.addEventListener('click', () => renderizarModuloMantenimiento('agencies'));

            container.querySelectorAll('[data-edit-agency]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const id = parseInt(btn.getAttribute('data-edit-agency'), 10);
                    const item = rows.find((x) => x.id === id);
                    if (!item) return;
                    editId = id;
                    document.getElementById('title-abm-agency').textContent = `Editando Agencia #${id}`;
                    document.getElementById('ag-nombre').value = item.nombre;
                    document.getElementById('ag-web').value = item.sitio_web;
                    document.getElementById('ag-tel').value = item.telefono_contacto || '';
                    document.getElementById('btn-submit-agency').textContent = 'Actualizar Agencia';
                    btnCancel.classList.remove('hidden');
                });
            });

            document.getElementById('form-abm-agency').addEventListener('submit', async (e) => {
                e.preventDefault();
                const payload = {
                    nombre: document.getElementById('ag-nombre').value,
                    sitio_web: document.getElementById('ag-web').value,
                    telefono_contacto: document.getElementById('ag-tel').value
                };
                try {
                    if (editId) {
                        await crudMantenimiento('agencies', 'PUT', payload, editId);
                        mostrarNotificacion(`Agencia #${editId} actualizada`);
                    } else {
                        await crudMantenimiento('agencies', 'POST', payload);
                        mostrarNotificacion('Agencia registrada en la base de datos');
                    }
                    state.catalogs = await obtenerCatalogos();
                    await renderizarModuloMantenimiento('agencies');
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
            });

            container.querySelectorAll('[data-del-agency]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    try {
                        await crudMantenimiento('agencies', 'DELETE', null, btn.getAttribute('data-del-agency'));
                        mostrarNotificacion('Agencia eliminada');
                        await renderizarModuloMantenimiento('agencies');
                    } catch (err) {
                        mostrarNotificacion(err.message);
                    }
                });
            });
        } else if (tab === 'neighborhoods') {
            const res = await crudMantenimiento('neighborhoods');
            const rows = res.data || [];
            let editId = null;
            const optsCiudad = state.catalogs.ciudades.map((c) => `<option value="${Number(c.id)}">${escapeHtml(c.nombre)}</option>`).join('');

            container.innerHTML = `
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <form id="form-abm-barrio" class="lg:col-span-4 bg-white border border-[#E4E4DF] rounded p-5 space-y-3 h-fit">
                        <h3 id="title-abm-barrio" class="font-mono-tech text-xs uppercase text-[#2E5A44] font-semibold">Alta de Barrio en Catálogo Maestro</h3>
                        <select id="bar-ciudad" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded">${optsCiudad}</select>
                        <input type="text" id="bar-nombre" required placeholder="Nombre del Barrio (Ej: Los Laureles)" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <div class="grid grid-cols-2 gap-2">
                            <input type="number" step="0.0001" id="bar-lat" value="-25.3015" required placeholder="Latitud" class="w-full px-3 py-2 text-xs font-mono-tech border border-[#D4D4CC] rounded" />
                            <input type="number" step="0.0001" id="bar-lon" value="-57.5712" required placeholder="Longitud" class="w-full px-3 py-2 text-xs font-mono-tech border border-[#D4D4CC] rounded" />
                        </div>
                        <div class="flex gap-2">
                            <button type="submit" id="btn-submit-barrio" class="tactile-btn flex-1 py-2 bg-[#121316] text-white text-xs font-mono-tech rounded">Guardar Barrio</button>
                            <button type="button" id="btn-cancel-barrio" class="hidden px-3 py-2 bg-[#F4F4F0] text-xs font-mono-tech border border-[#D4D4CC] rounded">Cancelar</button>
                        </div>
                    </form>
                    <div class="lg:col-span-8 bg-white border border-[#E4E4DF] rounded overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-[#F4F4F0] font-mono-tech uppercase text-[11px] text-[#52555A]">
                                <tr><th class="p-3">ID</th><th class="p-3">Ciudad</th><th class="p-3">Barrio</th><th class="p-3">Centroide GPS</th><th class="p-3">Acciones ABM</th></tr>
                            </thead>
                            <tbody class="divide-y divide-[#E4E4DF]">
                                ${rows.map((r) => `
                                    <tr>
                                        <td class="p-3 font-mono-tech">${Number(r.id)}</td>
                                        <td class="p-3">${escapeHtml(r.ciudad_nombre)}</td>
                                        <td class="p-3 font-semibold">${escapeHtml(r.nombre)}</td>
                                        <td class="p-3 font-mono-tech text-[#52555A]">${Number(r.lat_centroide)}, ${Number(r.lon_centroide)}</td>
                                        <td class="p-3 space-x-2 font-mono-tech">
                                            <button type="button" data-edit-barrio="${Number(r.id)}" class="text-[#2E5A44] hover:underline">Editar</button>
                                            <button type="button" data-del-barrio="${Number(r.id)}" class="text-[#B84A27] hover:underline">Eliminar</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            const btnCancel = document.getElementById('btn-cancel-barrio');
            btnCancel.addEventListener('click', () => renderizarModuloMantenimiento('neighborhoods'));

            container.querySelectorAll('[data-edit-barrio]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const id = parseInt(btn.getAttribute('data-edit-barrio'), 10);
                    const item = rows.find((x) => x.id === id);
                    if (!item) return;
                    editId = id;
                    document.getElementById('title-abm-barrio').textContent = `Editando Barrio #${id}`;
                    document.getElementById('bar-ciudad').value = item.ciudad_id;
                    document.getElementById('bar-nombre').value = item.nombre;
                    document.getElementById('bar-lat').value = item.lat_centroide;
                    document.getElementById('bar-lon').value = item.lon_centroide;
                    document.getElementById('btn-submit-barrio').textContent = 'Actualizar Barrio';
                    btnCancel.classList.remove('hidden');
                });
            });

            document.getElementById('form-abm-barrio').addEventListener('submit', async (e) => {
                e.preventDefault();
                const payload = {
                    ciudad_id: document.getElementById('bar-ciudad').value,
                    nombre: document.getElementById('bar-nombre').value,
                    lat_centroide: document.getElementById('bar-lat').value,
                    lon_centroide: document.getElementById('bar-lon').value
                };
                try {
                    if (editId) {
                        await crudMantenimiento('neighborhoods', 'PUT', payload, editId);
                        mostrarNotificacion(`Barrio #${editId} actualizado`);
                    } else {
                        await crudMantenimiento('neighborhoods', 'POST', payload);
                        mostrarNotificacion('Barrio agregado al catálogo geográfico');
                    }
                    state.catalogs = await obtenerCatalogos();
                    poblarSelectoresCatalogos();
                    await renderizarModuloMantenimiento('neighborhoods');
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
            });

            container.querySelectorAll('[data-del-barrio]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    try {
                        await crudMantenimiento('neighborhoods', 'DELETE', null, btn.getAttribute('data-del-barrio'));
                        mostrarNotificacion('Barrio eliminado');
                        await renderizarModuloMantenimiento('neighborhoods');
                    } catch (err) {
                        mostrarNotificacion(err.message);
                    }
                });
            });
        } else if (tab === 'cities') {
            const res = await crudMantenimiento('cities');
            const rows = res.data || [];
            let editId = null;

            container.innerHTML = `
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <form id="form-abm-city" class="lg:col-span-4 bg-white border border-[#E4E4DF] rounded p-5 space-y-3 h-fit">
                        <h3 id="title-abm-city" class="font-mono-tech text-xs uppercase text-[#2E5A44] font-semibold">Alta de Municipio / Ciudad</h3>
                        <input type="text" id="cit-nombre" required placeholder="Nombre (Ej: Capiatá)" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <input type="text" id="cit-depto" value="Central" required placeholder="Departamento" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <div class="flex gap-2">
                            <button type="submit" id="btn-submit-city" class="tactile-btn flex-1 py-2 bg-[#121316] text-white text-xs font-mono-tech rounded">Guardar Ciudad</button>
                            <button type="button" id="btn-cancel-city" class="hidden px-3 py-2 bg-[#F4F4F0] text-xs font-mono-tech border border-[#D4D4CC] rounded">Cancelar</button>
                        </div>
                    </form>
                    <div class="lg:col-span-8 bg-white border border-[#E4E4DF] rounded overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-[#F4F4F0] font-mono-tech uppercase text-[11px] text-[#52555A]">
                                <tr><th class="p-3">ID</th><th class="p-3">Ciudad</th><th class="p-3">Departamento</th><th class="p-3">Acciones ABM</th></tr>
                            </thead>
                            <tbody class="divide-y divide-[#E4E4DF]">
                                ${rows.map((r) => `
                                    <tr>
                                        <td class="p-3 font-mono-tech">${Number(r.id)}</td>
                                        <td class="p-3 font-semibold">${escapeHtml(r.nombre)}</td>
                                        <td class="p-3">${escapeHtml(r.departamento)}</td>
                                        <td class="p-3 space-x-2 font-mono-tech">
                                            <button type="button" data-edit-city="${Number(r.id)}" class="text-[#2E5A44] hover:underline">Editar</button>
                                            <button type="button" data-del-city="${Number(r.id)}" class="text-[#B84A27] hover:underline">Eliminar</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            const btnCancel = document.getElementById('btn-cancel-city');
            btnCancel.addEventListener('click', () => renderizarModuloMantenimiento('cities'));

            container.querySelectorAll('[data-edit-city]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const id = parseInt(btn.getAttribute('data-edit-city'), 10);
                    const item = rows.find((x) => x.id === id);
                    if (!item) return;
                    editId = id;
                    document.getElementById('title-abm-city').textContent = `Editando Ciudad #${id}`;
                    document.getElementById('cit-nombre').value = item.nombre;
                    document.getElementById('cit-depto').value = item.departamento;
                    document.getElementById('btn-submit-city').textContent = 'Actualizar Ciudad';
                    btnCancel.classList.remove('hidden');
                });
            });

            document.getElementById('form-abm-city').addEventListener('submit', async (e) => {
                e.preventDefault();
                const payload = {
                    nombre: document.getElementById('cit-nombre').value,
                    departamento: document.getElementById('cit-depto').value
                };
                try {
                    if (editId) {
                        await crudMantenimiento('cities', 'PUT', payload, editId);
                        mostrarNotificacion(`Ciudad #${editId} actualizada`);
                    } else {
                        await crudMantenimiento('cities', 'POST', payload);
                        mostrarNotificacion('Ciudad registrada');
                    }
                    state.catalogs = await obtenerCatalogos();
                    poblarSelectoresCatalogos();
                    await renderizarModuloMantenimiento('cities');
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
            });

            container.querySelectorAll('[data-del-city]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    try {
                        await crudMantenimiento('cities', 'DELETE', null, btn.getAttribute('data-del-city'));
                        mostrarNotificacion('Ciudad eliminada');
                        await renderizarModuloMantenimiento('cities');
                    } catch (err) {
                        mostrarNotificacion(err.message);
                    }
                });
            });
        } else if (tab === 'property-types') {
            const res = await crudMantenimiento('property-types');
            const rows = res.data || [];
            let editId = null;

            container.innerHTML = `
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <form id="form-abm-type" class="lg:col-span-4 bg-white border border-[#E4E4DF] rounded p-5 space-y-3 h-fit">
                        <h3 id="title-abm-type" class="font-mono-tech text-xs uppercase text-[#2E5A44] font-semibold">Alta de Tipo de Inmueble</h3>
                        <input type="text" id="typ-nombre" required placeholder="Nombre (Ej: Loft / Penthouse)" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <input type="text" id="typ-desc" placeholder="Descripción técnica" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <div class="flex gap-2">
                            <button type="submit" id="btn-submit-type" class="tactile-btn flex-1 py-2 bg-[#121316] text-white text-xs font-mono-tech rounded">Guardar Tipo</button>
                            <button type="button" id="btn-cancel-type" class="hidden px-3 py-2 bg-[#F4F4F0] text-xs font-mono-tech border border-[#D4D4CC] rounded">Cancelar</button>
                        </div>
                    </form>
                    <div class="lg:col-span-8 bg-white border border-[#E4E4DF] rounded overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-[#F4F4F0] font-mono-tech uppercase text-[11px] text-[#52555A]">
                                <tr><th class="p-3">ID</th><th class="p-3">Tipo</th><th class="p-3">Descripción</th><th class="p-3">Acciones ABM</th></tr>
                            </thead>
                            <tbody class="divide-y divide-[#E4E4DF]">
                                ${rows.map((r) => `
                                    <tr>
                                        <td class="p-3 font-mono-tech">${Number(r.id)}</td>
                                        <td class="p-3 font-semibold">${escapeHtml(r.nombre)}</td>
                                        <td class="p-3 text-[#52555A]">${escapeHtml(r.descripcion || '')}</td>
                                        <td class="p-3 space-x-2 font-mono-tech">
                                            <button type="button" data-edit-type="${Number(r.id)}" class="text-[#2E5A44] hover:underline">Editar</button>
                                            <button type="button" data-del-type="${Number(r.id)}" class="text-[#B84A27] hover:underline">Eliminar</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            const btnCancel = document.getElementById('btn-cancel-type');
            btnCancel.addEventListener('click', () => renderizarModuloMantenimiento('property-types'));

            container.querySelectorAll('[data-edit-type]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const id = parseInt(btn.getAttribute('data-edit-type'), 10);
                    const item = rows.find((x) => x.id === id);
                    if (!item) return;
                    editId = id;
                    document.getElementById('title-abm-type').textContent = `Editando Tipo #${id}`;
                    document.getElementById('typ-nombre').value = item.nombre;
                    document.getElementById('typ-desc').value = item.descripcion || '';
                    document.getElementById('btn-submit-type').textContent = 'Actualizar Tipo';
                    btnCancel.classList.remove('hidden');
                });
            });

            document.getElementById('form-abm-type').addEventListener('submit', async (e) => {
                e.preventDefault();
                const payload = {
                    nombre: document.getElementById('typ-nombre').value,
                    descripcion: document.getElementById('typ-desc').value
                };
                try {
                    if (editId) {
                        await crudMantenimiento('property-types', 'PUT', payload, editId);
                        mostrarNotificacion(`Tipo #${editId} actualizado`);
                    } else {
                        await crudMantenimiento('property-types', 'POST', payload);
                        mostrarNotificacion('Tipo de inmueble creado');
                    }
                    state.catalogs = await obtenerCatalogos();
                    poblarSelectoresCatalogos();
                    await renderizarModuloMantenimiento('property-types');
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
            });

            container.querySelectorAll('[data-del-type]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    try {
                        await crudMantenimiento('property-types', 'DELETE', null, btn.getAttribute('data-del-type'));
                        mostrarNotificacion('Tipo eliminado');
                        await renderizarModuloMantenimiento('property-types');
                    } catch (err) {
                        mostrarNotificacion(err.message);
                    }
                });
            });
        } else if (tab === 'users') {
            const res = await crudMantenimiento('users');
            const rows = res.data || [];
            let editId = null;

            container.innerHTML = `
                <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                    <form id="form-abm-user" class="lg:col-span-4 bg-white border border-[#E4E4DF] rounded p-5 space-y-3 h-fit">
                        <h3 id="title-abm-user" class="font-mono-tech text-xs uppercase text-[#2E5A44] font-semibold">Alta de Usuario del Sistema</h3>
                        <div class="grid grid-cols-2 gap-2">
                            <input type="text" id="usr-nombre" required placeholder="Nombre" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                            <input type="text" id="usr-apellido" required placeholder="Apellido" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        </div>
                        <input type="email" id="usr-email" required placeholder="correo@dominio.com" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <input type="password" id="usr-pass" placeholder="Contraseña (mín. 6 caracteres)" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded" />
                        <select id="usr-rol" class="w-full px-3 py-2 text-xs border border-[#D4D4CC] rounded">
                            <option value="2">Rol: Cliente</option>
                            <option value="1">Rol: Administrador</option>
                        </select>
                        <div class="flex gap-2">
                            <button type="submit" id="btn-submit-user" class="tactile-btn flex-1 py-2 bg-[#121316] text-white text-xs font-mono-tech rounded">Registrar Usuario</button>
                            <button type="button" id="btn-cancel-user" class="hidden px-3 py-2 bg-[#F4F4F0] text-xs font-mono-tech border border-[#D4D4CC] rounded">Cancelar</button>
                        </div>
                    </form>
                    <div class="lg:col-span-8 bg-white border border-[#E4E4DF] rounded overflow-x-auto">
                        <table class="w-full text-left text-xs">
                            <thead class="bg-[#F4F4F0] font-mono-tech uppercase text-[11px] text-[#52555A]">
                                <tr><th class="p-3">ID</th><th class="p-3">Nombre</th><th class="p-3">Email</th><th class="p-3">Rol</th><th class="p-3">Acciones ABM</th></tr>
                            </thead>
                            <tbody class="divide-y divide-[#E4E4DF]">
                                ${rows.map((r) => `
                                    <tr>
                                        <td class="p-3 font-mono-tech">${Number(r.id)}</td>
                                        <td class="p-3 font-semibold">${escapeHtml(r.nombre_completo)}</td>
                                        <td class="p-3 font-mono-tech text-[#52555A]">${escapeHtml(r.email)}</td>
                                        <td class="p-3 font-mono-tech">${escapeHtml(r.rol_nombre)}</td>
                                        <td class="p-3 space-x-2 font-mono-tech">
                                            <button type="button" data-edit-user="${Number(r.id)}" class="text-[#2E5A44] hover:underline">Editar</button>
                                            <button type="button" data-del-user="${Number(r.id)}" class="text-[#B84A27] hover:underline">Eliminar</button>
                                        </td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                </div>
            `;

            const btnCancel = document.getElementById('btn-cancel-user');
            btnCancel.addEventListener('click', () => renderizarModuloMantenimiento('users'));

            container.querySelectorAll('[data-edit-user]').forEach((btn) => {
                btn.addEventListener('click', () => {
                    const id = parseInt(btn.getAttribute('data-edit-user'), 10);
                    const item = rows.find((x) => x.id === id);
                    if (!item) return;
                    editId = id;
                    document.getElementById('title-abm-user').textContent = `Editando Usuario #${id}`;
                    document.getElementById('usr-nombre').value = item.nombre;
                    document.getElementById('usr-apellido').value = item.apellido;
                    document.getElementById('usr-email').value = item.email;
                    document.getElementById('usr-email').disabled = true;
                    document.getElementById('usr-rol').value = item.rol_id;
                    document.getElementById('btn-submit-user').textContent = 'Actualizar Usuario';
                    btnCancel.classList.remove('hidden');
                });
            });

            document.getElementById('form-abm-user').addEventListener('submit', async (e) => {
                e.preventDefault();
                const payload = {
                    nombre: document.getElementById('usr-nombre').value,
                    apellido: document.getElementById('usr-apellido').value,
                    email: document.getElementById('usr-email').value,
                    rol_id: document.getElementById('usr-rol').value
                };
                const passVal = document.getElementById('usr-pass').value;
                if (passVal) payload.password = passVal;

                try {
                    if (editId) {
                        await crudMantenimiento('users', 'PUT', payload, editId);
                        mostrarNotificacion(`Usuario #${editId} actualizado`);
                    } else {
                        await crudMantenimiento('users', 'POST', payload);
                        mostrarNotificacion('Usuario creado correctamente');
                    }
                    await renderizarModuloMantenimiento('users');
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
            });

            container.querySelectorAll('[data-del-user]').forEach((btn) => {
                btn.addEventListener('click', async () => {
                    try {
                        await crudMantenimiento('users', 'DELETE', null, btn.getAttribute('data-del-user'));
                        mostrarNotificacion('Usuario eliminado');
                        await renderizarModuloMantenimiento('users');
                    } catch (err) {
                        mostrarNotificacion(err.message);
                    }
                });
            });
        } else if (tab === 'test-dedup') {
            const optsAgencia = state.catalogs.agencias.map((a) => `<option value="${Number(a.id)}">${escapeHtml(a.nombre)}</option>`).join('');
            container.innerHTML = `
                <div class="max-w-2xl bg-white border border-[#E4E4DF] rounded p-6 space-y-4">
                    <div>
                        <span class="font-mono-tech text-[11px] uppercase text-[#2E5A44]">PRUEBA DEL ALGORITMO DE SCORING (UMBRAL >= 75 PTS)</span>
                        <h3 class="font-editorial text-2xl text-[#121316]">Ingresar Aviso para Deduplicación Automática</h3>
                        <p class="text-xs text-[#52555A]">
                            Si ingresa una publicación con datos cercanos a un inmueble existente en el mismo barrio (ej: Edificio Feel en Villa Morra, 2 dorm, ~88 m²), el motor de puntaje lo agrupará automáticamente.
                        </p>
                    </div>
                    <form id="form-sim-dedup" class="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                        <div>
                            <label class="block font-mono-tech text-[11px] text-[#52555A] mb-1">Agencia Origen</label>
                            <select id="sim-agencia" class="w-full px-3 py-2 border border-[#D4D4CC] rounded">${optsAgencia}</select>
                        </div>
                        <div>
                            <label class="block font-mono-tech text-[11px] text-[#52555A] mb-1">Barrio</label>
                            <input type="text" id="sim-barrio" value="Villa Morra" required class="w-full px-3 py-2 border border-[#D4D4CC] rounded" />
                        </div>
                        <div class="sm:col-span-2">
                            <label class="block font-mono-tech text-[11px] text-[#52555A] mb-1">Título del Aviso</label>
                            <input type="text" id="sim-titulo" value="Alquilo Dpto 2 Dormitorios en Edificio Feel - Villa Morra" required class="w-full px-3 py-2 border border-[#D4D4CC] rounded" />
                        </div>
                        <div>
                            <label class="block font-mono-tech text-[11px] text-[#52555A] mb-1">Precio en Guaraníes (PYG)</label>
                            <input type="number" id="sim-precio" value="6050000" required class="w-full px-3 py-2 font-mono-tech border border-[#D4D4CC] rounded" />
                        </div>
                        <div>
                            <label class="block font-mono-tech text-[11px] text-[#52555A] mb-1">Expensas (PYG)</label>
                            <input type="number" id="sim-expensas" value="250000" required class="w-full px-3 py-2 font-mono-tech border border-[#D4D4CC] rounded" />
                        </div>
                        <div>
                            <label class="block font-mono-tech text-[11px] text-[#52555A] mb-1">Superficie m²</label>
                            <input type="number" id="sim-m2" value="87" required class="w-full px-3 py-2 font-mono-tech border border-[#D4D4CC] rounded" />
                        </div>
                        <div>
                            <label class="block font-mono-tech text-[11px] text-[#52555A] mb-1">Dormitorios</label>
                            <input type="number" id="sim-dorm" value="2" required class="w-full px-3 py-2 font-mono-tech border border-[#D4D4CC] rounded" />
                        </div>
                        <div class="sm:col-span-2 pt-2">
                            <button type="submit" class="tactile-btn w-full py-2.5 bg-[#2E5A44] text-white font-mono-tech uppercase rounded">
                                Procesar Aviso en Motor de Deduplicación
                            </button>
                        </div>
                    </form>
                </div>
            `;

            document.getElementById('form-sim-dedup').addEventListener('submit', async (e) => {
                e.preventDefault();
                try {
                    const res = await crudMantenimiento('listings', 'POST', {
                        agencia_id: parseInt(document.getElementById('sim-agencia').value, 10),
                        url_externa: `https://www.infocasas.com.py/aviso-simulado-${Date.now()}`,
                        titulo_original: document.getElementById('sim-titulo').value,
                        barrio_nombre: document.getElementById('sim-barrio').value,
                        tipo_inmueble: 'Departamento',
                        tipo_operacion: 'alquiler',
                        moneda_original: 'PYG',
                        precio_original: parseFloat(document.getElementById('sim-precio').value),
                        expensas_original: parseFloat(document.getElementById('sim-expensas').value),
                        superficie_m2: parseFloat(document.getElementById('sim-m2').value),
                        dormitorios: parseInt(document.getElementById('sim-dorm').value, 10),
                        banos: 2
                    });
                    mostrarNotificacion(res.message);
                    await ejecutarBusquedaFiltrada();
                } catch (err) {
                    mostrarNotificacion(err.message);
                }
            });
        }
    } catch (err) {
        container.innerHTML = `<div class="p-5 bg-white border border-[#B84A27] rounded text-xs font-mono-tech text-[#B84A27]">${escapeHtml(err.message)}</div>`;
    }
}

// =============================================================================
// 7. INICIALIZACIÓN GENERAL DE LA APLICACIÓN
// =============================================================================

document.addEventListener('DOMContentLoaded', async () => {
    iniciarKeepAlive();
    configurarEventosLogin();

    try {
        const sesion = await obtenerSesionActual();
        state.currentUser = sesion.user || null;
    } catch (_) {
        state.currentUser = null;
    }
    actualizarInterfazSesion();

    try {
        state.catalogs = await obtenerCatalogos();
        poblarSelectoresCatalogos();
    } catch (_) {}

    inicializarMapa('leaflet-map');
    await ejecutarBusquedaFiltrada();
    await cargarAnaliticaM2();

    document.querySelectorAll('.nav-tab').forEach((btn) => {
        btn.addEventListener('click', () => {
            cambiarVistaMenu(btn.getAttribute('data-nav'));
        });
    });

    document.getElementById('btn-back-to-search').addEventListener('click', () => {
        cambiarVistaMenu('explorador');
    });

    document.getElementById('search-filters-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        await ejecutarBusquedaFiltrada();
    });

    document.getElementById('btn-reset-filters').addEventListener('click', async () => {
        document.getElementById('search-filters-form').reset();
        await ejecutarBusquedaFiltrada();
    });

    document.querySelectorAll('.maint-tab').forEach((btn) => {
        btn.addEventListener('click', () => {
            renderizarModuloMantenimiento(btn.getAttribute('data-maint'));
        });
    });

    document.getElementById('btn-trigger-scraper').addEventListener('click', async () => {
        try {
            mostrarNotificacion('Ejecutando scrapers de RE/MAX e InfoCasas...');
            const res = await ejecutarScraperEnVivo();
            mostrarNotificacion(res.message);
            await ejecutarBusquedaFiltrada();
        } catch (err) {
            mostrarNotificacion(err.message);
        }
    });

    document.getElementById('btn-refresh-movements').addEventListener('click', () => {
        renderizarModuloMovimientos();
    });

    const params = new URLSearchParams(window.location.search);
    if (params.get('compare')) {
        cambiarVistaMenu('comparador', parseInt(params.get('compare'), 10));
    }
});
