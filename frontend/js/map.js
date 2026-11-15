// =============================================================================
// MÓDULO DE MAPA Y GEORREFERENCIACIÓN (frontend/js/map.js)
// Utiliza Leaflet.js + Leaflet.markercluster con sanitización anti-XSS
// =============================================================================

let mapInstance = null;
let clusterGroup = null;

/**
 * Escapa caracteres HTML especiales para prevenir ataques XSS en popups del mapa.
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
 * Formatea un monto en Guaraníes de forma compacta para el pin del mapa (Ej: Gs. 6.2M).
 */
function formatearPrecioCortoPyg(monto) {
    const valor = Number(monto || 0);
    if (valor >= 1000000000) {
        return `Gs. ${(valor / 1000000000).toFixed(2)}B`;
    }
    if (valor >= 1000000) {
        return `Gs. ${(valor / 1000000).toFixed(1)}M`;
    }
    return `Gs. ${valor.toLocaleString('es-PY')}`;
}

/**
 * Inicializa el mapa OpenStreetMap centrado en Asunción y configura el plugin MarkerCluster.
 */
export function inicializarMapa(elementId = 'leaflet-map', coords = [-25.2885, -57.5750], zoom = 13) {
    if (mapInstance) {
        mapInstance.invalidateSize();
        return mapInstance;
    }

    mapInstance = L.map(elementId, {
        zoomControl: true,
        scrollWheelZoom: true
    }).setView(coords, zoom);

    // Capa de teselas OpenStreetMap gratuita
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; OpenStreetMap Paraguay'
    }).addTo(mapInstance);

    // Inicializa el grupo de clusters con diseño minimalista en monoespaciado
    clusterGroup = L.markerClusterGroup({
        showCoverageOnHover: false,
        maxClusterRadius: 42,
        iconCreateFunction: function (cluster) {
            const count = Number(cluster.getChildCount());
            return L.divIcon({
                html: `<span>${count}</span>`,
                className: 'custom-cluster-icon',
                iconSize: L.point(34, 34)
            });
        }
    });

    mapInstance.addLayer(clusterGroup);
    return mapInstance;
}

/**
 * Renderiza los marcadores de propiedades en el mapa sanitizando textos dinámicos.
 */
export function actualizarMarcadoresMapa(propiedades, onSelectProperty) {
    if (!mapInstance || !clusterGroup) return;

    clusterGroup.clearLayers();
    const bounds = [];

    propiedades.forEach((item) => {
        if (!item.latitud || !item.longitud) return;

        const etiquetaPrecio = escapeHtml(formatearPrecioCortoPyg(item.precio_min_pyg));
        const claseArbitraje = item.es_duplicado ? 'is-arbitrage' : '';
        const indicadorAgencias = item.es_duplicado ? ` · ${Number(item.cantidad_agencias)} ag.` : '';

        // Crea el pin HTML con estética técnica editorial
        const customIcon = L.divIcon({
            className: 'bg-transparent border-0',
            html: `<div class="price-pin ${claseArbitraje}">${etiquetaPrecio}${indicadorAgencias}</div>`,
            iconSize: [110, 26],
            iconAnchor: [55, 13]
        });

        const marker = L.marker([Number(item.latitud), Number(item.longitud)], { icon: customIcon });

        // Contenido del popup sanitizado contra XSS
        const ahorroHtml = item.diferencia_pyg > 0
            ? `<div class="mt-1 text-xs font-mono-tech text-[#2E5A44] font-semibold">
                 Diferencia detectada: Gs. ${Number(item.diferencia_pyg).toLocaleString('es-PY')}
               </div>`
            : '';

        const popupDiv = document.createElement('div');
        popupDiv.className = 'p-1 min-w-[210px] font-sans text-[#121316]';
        popupDiv.innerHTML = `
            <div class="text-[11px] font-mono-tech uppercase tracking-wider text-[#52555A]">
                ${escapeHtml(item.barrio)} · ${escapeHtml(item.tipo_inmueble)}
            </div>
            <div class="font-semibold text-sm mt-0.5 leading-snug">${escapeHtml(item.titulo_canonico)}</div>
            <div class="mt-1.5 text-xs font-mono-tech">
                Desde: <strong>Gs. ${Number(item.precio_min_pyg).toLocaleString('es-PY')}</strong>
            </div>
            ${ahorroHtml}
            <button type="button" class="btn-ver-comparativa mt-2.5 w-full py-1.5 px-2.5 bg-[#121316] text-[#FBFBF9] text-xs font-medium rounded hover:bg-[#2a2c32] transition-colors">
                Inspeccionar ${Number(item.cantidad_agencias)} publicación(es)
            </button>
        `;

        popupDiv.querySelector('.btn-ver-comparativa').addEventListener('click', () => {
            if (typeof onSelectProperty === 'function') {
                onSelectProperty(item.id);
            }
        });

        marker.bindPopup(popupDiv);
        clusterGroup.addLayer(marker);
        bounds.push([Number(item.latitud), Number(item.longitud)]);
    });

    if (bounds.length > 0) {
        mapInstance.fitBounds(bounds, { padding: [35, 35], maxZoom: 15 });
    }
}

/**
 * Centra la cámara del mapa sobre una propiedad específica al seleccionarla en la lista.
 */
export function enfocarPropiedadEnMapa(lat, lon) {
    if (!mapInstance || !lat || !lon) return;
    mapInstance.setView([Number(lat), Number(lon)], 16, { animate: true });
}
