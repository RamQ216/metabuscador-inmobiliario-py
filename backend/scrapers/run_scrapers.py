from scrapers.scraper_remax import extraer_avisos_remax
from scrapers.scraper_infocasas import extraer_avisos_infocasas
from app.services.deduplication import procesar_y_guardar_publicacion


def ejecutar_pipeline_scraping():
    """
    Orquesta la ejecución de los scrapers de RE/MAX e InfoCasas, normaliza los precios
    a Guaraníes y agrupa automáticamente los avisos duplicados por puntaje.
    """
    avisos_remax = extraer_avisos_remax()
    avisos_infocasas = extraer_avisos_infocasas()

    todos_los_avisos = avisos_remax + avisos_infocasas
    nuevos_procesados = 0
    duplicados_agrupados = 0

    for aviso in todos_los_avisos:
        _, fue_agrupado = procesar_y_guardar_publicacion(aviso)
        nuevos_procesados += 1
        if fue_agrupado:
            duplicados_agrupados += 1

    return {
        'total_extraidos': nuevos_procesados,
        'duplicados_cruzados': duplicados_agrupados
    }
