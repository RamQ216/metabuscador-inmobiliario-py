import time
import requests
from app.config import Config

# Caché en memoria con tiempo de expiración (TTL) para mantener fresca la cotización
_cached_rate = None
_cache_timestamp = 0.0


def obtener_cotizacion_usd_pyg():
    """
    Consulta la cotización actual del Dólar (USD) a Guaraníes (PYG) desde una API abierta
    paraguaya (dolarpy) con caché TTL de 6 horas, o devuelve la tasa referencial del BCP.
    """
    global _cached_rate, _cache_timestamp
    ahora = time.time()

    # Retorna el valor en caché solo si no ha expirado el TTL configurado
    if _cached_rate is not None and (ahora - _cache_timestamp) < Config.CURRENCY_CACHE_TTL_SECONDS:
        return _cached_rate

    try:
        # Consulta API pública de cotizaciones de Paraguay con timeout corto
        response = requests.get('https://dolar.melizeche.com/api/1.0/', timeout=3)
        if response.status_code == 200:
            data = response.json()
            bcp_rate = data.get('dolarpy', {}).get('bcp', {}).get('venta')
            if bcp_rate and float(bcp_rate) > 5000:
                _cached_rate = float(bcp_rate)
                _cache_timestamp = ahora
                return _cached_rate
    except Exception:
        # Si no hay internet o la API falla, utiliza el valor por defecto configurado
        pass

    _cached_rate = Config.DEFAULT_USD_TO_PYG
    _cache_timestamp = ahora
    return _cached_rate


def normalizar_a_guaranies(monto, moneda='PYG'):
    """
    Convierte cualquier monto en USD o PYG a Guaraníes (PYG) para que todo el sistema
    mantenga los precios unificados en moneda local (Decisión de diseño MVP).
    """
    monto_float = float(monto or 0)
    moneda_limpia = (moneda or 'PYG').upper().strip()

    if moneda_limpia in ('USD', 'U$S', 'US$', '$'):
        tasa = obtener_cotizacion_usd_pyg()
        return round(monto_float * tasa, 0)

    return round(monto_float, 0)
