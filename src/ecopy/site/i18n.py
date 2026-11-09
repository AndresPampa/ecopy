"""Textos del sitio en cada idioma y etiquetas de la taxonomía."""

from __future__ import annotations

from collections.abc import Mapping

TEXTS = {
    "en": {
        "switch_label": "Español",
        "first_data": "First day with data",
        "last_closed": "Last closed month",
        "yearly_title": "Downloads per year",
        "monthly_title": "Downloads per month",
        "year": "Year",
        "month": "Month",
        "downloads": "Downloads",
        "status": "Status",
        "package_start": "Since first release",
        "source_gap": "Source gaps ({with_data} of {expected} days)",
        "degraded": "Degraded days ({degraded})",
        "ytd": "Year to date",
        "in_progress": "In progress",
        "complete": "Complete",
        "no_data": "No data",
        "chart_alt": "Line chart of downloads per month. The table has the same data.",
        "in_progress_note": (
            "{month} in progress: {downloads} downloads in {days} of {total} days. The line stops "
            "at the last closed month."
        ),
        "discontinuity_mark": "discontinuity",
        "main_nav": "Main",
        "nav_years": "Years",
        "nav_libraries": "Libraries",
        "nav_compare": "Compare",
        "nav_python": "Python",
        "finding": "{domain} went from {first} of catalog downloads in {y0} to {last} in {y1}.",
        "strata_alt": "Columns with the share of each domain per year. The legend has the values.",
        "strata_caption": (
            "Share of each domain in catalog downloads. Each column opens its year. A fainter "
            "column is a year in progress."
        ),
        "in_year": "in {year}",
        "trend_alt": "Share of PyPI over the last 36 closed months for {project}.",
        "catalog_title": "Libraries",
        "catalog_lead": "The ecopy catalog, by downloads in the last closed month.",
        "trend_col": "Share of PyPI, 36 months",
        "filter_label": "Filter by tag",
        "filter_count": "{shown} of {total} libraries",
        "last_month_col": "Last closed month",
        "movers_home": "Biggest gains in {year}",
        "movers_unit": "In share points.",
        "explore_domains": "Explore by domain",
        "libraries_count": "{n} libraries",
        "share_year_title": "Share of catalog downloads per year",
        "share_year_alt": "Bars with the share per year. The table has the same data.",
        "share_year_note": "A fainter bar is a year in progress.",
        "categories_title": "Categories",
        "top_libraries": "Most downloaded libraries",
        "in_domain": "Domain",
        "python_page_title": "Python releases",
        "python_lead": "Every CPython minor version, with its release and end of support.",
        "released": "Released",
        "end_of_support": "End of support",
        "support_supported": "Supported",
        "support_end_of_life": "End of life",
        "support_unknown": "Not published",
        "lifecycle_alt": (
            "Bars from release to end of support per version. The table has the dates."
        ),
        "today": "today",
        "compare_title": "Compare libraries",
        "compare_lead": "Up to four libraries on one chart. The link keeps your selection.",
        "compare_add": "Add a library",
        "compare_button": "Add",
        "compare_remove": "Remove {project}",
        "compare_full": "Four libraries at most: remove one to add another.",
        "compare_unknown": "That library is not in the catalog.",
        "compare_empty": "Choose at least one library.",
        "compare_failed": "The data could not be loaded.",
        "compare_measure": "Measure",
        "compare_scale": "Scale",
        "measure_share": "Share of PyPI",
        "measure_downloads": "Downloads",
        "scale_linear": "Linear",
        "scale_log": "Logarithmic",
        "compare_alt": "Line chart of the selected libraries. The table has the same data.",
        "compare_noscript": "The comparator needs JavaScript. Each library page has its own data.",
        "compare_examples": "Examples",
        "compare_table": "Data table",
        "share_title": "Share of all PyPI downloads",
        "share_alt": "Line chart of the monthly share of PyPI.",
        "share_note": "Share is less affected by CI inflation than absolute downloads.",
        "stars_title": "GitHub stars",
        "stars_alt": "Line chart of accumulated stars per week.",
        "stars_note": (
            "History is net: it only counts people who still have the star, dated when they gave "
            "it. Old repositories can show a jump in their first week."
        ),
        "stars_total": "{total} stars in {repo}",
        "stars_shared": "This repository also publishes:",
        "stars_none": "No star data yet.",
        "no_repo": "No GitHub repository.",
        "renamed_from": "Formerly",
        "renamed_to": "Now published as",
        "repository": "Repository",
        "source": "Data: ClickPy, from PyPI download logs.",
        "last_updated": "Last updated",
        "update_failed": "Update failed: the latest ingest did not pass validation.",
        "update_failed_since": "Figures are from the last good update, on {date}.",
        "years_title": "The Python ecosystem, year by year",
        "compared_with": "Compared with the same number of days from {start} to {end}.",
        "methodology": "Methodology version {version}.",
        "volume_title": "Total downloads on PyPI",
        "volume_warning": (
            "This volume is inflated by CI and grows for reasons unrelated to popularity: it is "
            "not a measure of real users."
        ),
        "volume_alt": "Bar chart of total downloads per year. The table has the same data.",
        "volume_note": (
            "* Year with a change in data collection. A lighter bar is a year in progress."
        ),
        "against_previous": "against the previous period.",
        "growth_hidden": "Growth is not shown: the comparison crosses a change in data collection.",
        "discontinuity": "The volume has a discontinuity on",
        "shares_title": "Share by domain and category",
        "shares_alt": "Bar chart of the twelve largest categories. The table has all of them.",
        "catalog_share": (
            "Shares are over the ecopy catalog, which is {share} of all PyPI downloads this period."
        ),
        "category": "Category",
        "share": "Share",
        "package": "Package",
        "share_points": "Change (share points)",
        "position": "Position",
        "movers_title": "Movers",
        "movers_up": "Biggest gains",
        "movers_down": "Biggest losses",
        "movers_note": (
            "Packages most people never install on purpose (the Foundations category) are left "
            "out of this list."
        ),
        "no_previous": "Not available: 2017 has no complete previous year to compare with.",
        "newcomers_title": "New in the top 100",
        "top_position": "Position in PyPI",
        "no_newcomers": "No new packages this period.",
        "python_title": "Python versions",
        "python_alt": (
            "Bar chart of the Python versions with at least 1% of downloads. The table has all of"
            " them."
        ),
        "python_note": (
            "Closed months only. Without a version: {unknown}. Other values that are not CPython "
            "releases: {other}."
        ),
        "version": "Version",
        "leading_title": "Most used version per year",
        "timeline_title": "Python timeline",
        "event_release": "released",
        "event_end_of_life": "end of support",
        "no_events": "No releases or end of support this period.",
    },
    "es": {
        "switch_label": "English",
        "first_data": "Primer día con datos",
        "last_closed": "Último mes cerrado",
        "yearly_title": "Descargas por año",
        "monthly_title": "Descargas por mes",
        "year": "Año",
        "month": "Mes",
        "downloads": "Descargas",
        "status": "Estado",
        "package_start": "Desde el primer release",
        "source_gap": "Huecos de la fuente ({with_data} de {expected} días)",
        "degraded": "Días degradados ({degraded})",
        "ytd": "Año en curso",
        "in_progress": "En curso",
        "complete": "Completo",
        "no_data": "Sin datos",
        "chart_alt": "Gráfico de líneas de descargas por mes. La tabla tiene los mismos datos.",
        "in_progress_note": (
            "{month} en curso: {downloads} descargas en {days} de {total} días. La línea termina "
            "en el último mes cerrado."
        ),
        "discontinuity_mark": "discontinuidad",
        "main_nav": "Principal",
        "nav_years": "Años",
        "nav_libraries": "Librerías",
        "nav_compare": "Comparar",
        "nav_python": "Python",
        "finding": (
            "{domain} pasó de {first} de las descargas del catálogo en {y0} a {last} en {y1}."
        ),
        "strata_alt": (
            "Columnas con la cuota de cada dominio por año. La leyenda tiene los valores."
        ),
        "strata_caption": (
            "Cuota de cada dominio sobre las descargas del catálogo. Cada columna abre su año. "
            "Una columna más tenue es un año en curso."
        ),
        "in_year": "en {year}",
        "trend_alt": "Cuota de PyPI de los últimos 36 meses cerrados de {project}.",
        "catalog_title": "Librerías",
        "catalog_lead": "El catálogo de ecopy, por descargas del último mes cerrado.",
        "trend_col": "Cuota de PyPI, 36 meses",
        "filter_label": "Filtrar por tag",
        "filter_count": "{shown} de {total} librerías",
        "last_month_col": "Último mes cerrado",
        "movers_home": "Mayores subas de {year}",
        "movers_unit": "En puntos de cuota.",
        "explore_domains": "Explorar por dominio",
        "libraries_count": "{n} librerías",
        "share_year_title": "Cuota de las descargas del catálogo por año",
        "share_year_alt": "Barras con la cuota por año. La tabla tiene los mismos datos.",
        "share_year_note": "Una barra más tenue es un año en curso.",
        "categories_title": "Categorías",
        "top_libraries": "Librerías más descargadas",
        "in_domain": "Dominio",
        "python_page_title": "Versiones de Python",
        "python_lead": "Cada versión menor de CPython, con su lanzamiento y fin de soporte.",
        "released": "Lanzamiento",
        "end_of_support": "Fin de soporte",
        "support_supported": "Con soporte",
        "support_end_of_life": "Sin soporte",
        "support_unknown": "No publicado",
        "lifecycle_alt": (
            "Barras de lanzamiento a fin de soporte por versión. La tabla tiene las fechas."
        ),
        "today": "hoy",
        "compare_title": "Comparar librerías",
        "compare_lead": "Hasta cuatro librerías en un gráfico. El enlace conserva tu selección.",
        "compare_add": "Agregar una librería",
        "compare_button": "Agregar",
        "compare_remove": "Quitar {project}",
        "compare_full": "Cuatro librerías como máximo: quitá una para agregar otra.",
        "compare_unknown": "Esa librería no está en el catálogo.",
        "compare_empty": "Elegí al menos una librería.",
        "compare_failed": "No se pudieron cargar los datos.",
        "compare_measure": "Medida",
        "compare_scale": "Escala",
        "measure_share": "Cuota de PyPI",
        "measure_downloads": "Descargas",
        "scale_linear": "Lineal",
        "scale_log": "Logarítmica",
        "compare_alt": (
            "Gráfico de líneas de las librerías elegidas. La tabla tiene los mismos datos."
        ),
        "compare_noscript": (
            "El comparador necesita JavaScript. Cada ficha tiene sus propios datos."
        ),
        "compare_examples": "Ejemplos",
        "compare_table": "Tabla de datos",
        "share_title": "Cuota de todas las descargas de PyPI",
        "share_alt": "Gráfico de líneas de la cuota mensual de PyPI.",
        "share_note": "La cuota se ve menos afectada por la inflación de CI que las descargas.",
        "stars_title": "Estrellas en GitHub",
        "stars_alt": "Gráfico de líneas de las estrellas acumuladas por semana.",
        "stars_note": (
            "La historia es neta: solo cuenta a quienes conservan la estrella, fechada cuando la "
            "dieron. Los repos viejos pueden mostrar un salto en su primera semana."
        ),
        "stars_total": "{total} estrellas en {repo}",
        "stars_shared": "Este repositorio también publica:",
        "stars_none": "Todavía sin datos de estrellas.",
        "no_repo": "Sin repositorio en GitHub.",
        "renamed_from": "Antes",
        "renamed_to": "Ahora se publica como",
        "repository": "Repositorio",
        "source": "Datos: ClickPy, a partir de los registros de descargas de PyPI.",
        "last_updated": "Última actualización",
        "update_failed": "Actualización fallida: la última ingesta no pasó la validación.",
        "update_failed_since": "Las cifras son las de la última actualización válida, del {date}.",
        "years_title": "El ecosistema Python, año por año",
        "compared_with": "Comparado con la misma cantidad de días, del {start} al {end}.",
        "methodology": "Versión metodológica {version}.",
        "volume_title": "Descargas totales en PyPI",
        "volume_warning": (
            "Este volumen está inflado por CI y crece por razones ajenas a la popularidad: no "
            "mide usuarios reales."
        ),
        "volume_alt": (
            "Gráfico de barras de descargas totales por año. La tabla tiene los mismos datos."
        ),
        "volume_note": (
            "* Año con un cambio en la recolección de datos. Una barra más clara es un año en "
            "curso."
        ),
        "against_previous": "contra el período anterior.",
        "growth_hidden": (
            "El crecimiento no se muestra: la comparación cruza un cambio en la recolección de "
            "datos."
        ),
        "discontinuity": "El volumen tiene una discontinuidad el",
        "shares_title": "Cuota por dominio y categoría",
        "shares_alt": (
            "Gráfico de barras de las doce categorías más grandes. La tabla las tiene todas."
        ),
        "catalog_share": (
            "Las cuotas son sobre el catálogo de ecopy, que representa {share} de las descargas "
            "de PyPI en este período."
        ),
        "category": "Categoría",
        "share": "Cuota",
        "package": "Paquete",
        "share_points": "Cambio (puntos de cuota)",
        "position": "Posición",
        "movers_title": "Movers",
        "movers_up": "Mayores subas",
        "movers_down": "Mayores bajas",
        "movers_note": (
            "Los paquetes que casi nadie instala a propósito (la categoría Infraestructura base) "
            "no entran en esta lista."
        ),
        "no_previous": (
            "No disponible: 2017 no tiene un año anterior completo con el cual comparar."
        ),
        "newcomers_title": "Nuevos en el top 100",
        "top_position": "Posición en PyPI",
        "no_newcomers": "Sin paquetes nuevos en este período.",
        "python_title": "Versiones de Python",
        "python_alt": (
            "Gráfico de barras de las versiones de Python con al menos 1 % de las descargas. La "
            "tabla las tiene todas."
        ),
        "python_note": (
            "Solo meses cerrados. Sin versión: {unknown}. Otros valores que no son versiones de "
            "CPython: {other}."
        ),
        "version": "Versión",
        "leading_title": "Versión más usada por año",
        "timeline_title": "Línea de tiempo de Python",
        "event_release": "lanzamiento",
        "event_end_of_life": "fin de soporte",
        "no_events": "Sin lanzamientos ni fin de soporte en este período.",
    },
}


def label(slug: str, labels: Mapping, lang: str) -> str:
    return labels.get(slug, {}).get(lang) or slug
