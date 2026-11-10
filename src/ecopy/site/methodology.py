"""Textos de la página de metodología. Las fechas y la versión vienen del código, no de acá."""

from __future__ import annotations

from datetime import date

DISCONTINUITY_NOTES = {
    "en": {
        date(2018, 7, 27): "Total volume triples and never returns to its previous level.",
        date(2026, 8, 25): (
            "Total volume falls 36 % from one day to the next and recovers slowly. Cause unknown."
        ),
    },
    "es": {
        date(2018, 7, 27): "El volumen total se triplica y no vuelve a su nivel anterior.",
        date(2026, 8, 25): (
            "El volumen total cae 36 % de un día para el otro y se recupera despacio. Causa "
            "desconocida."
        ),
    },
}

TEXTS = {
    "en": {
        "lead": (
            "Where every figure on ecopy comes from, how it is calculated and what it cannot tell "
            "you."
        ),
        "version": "Current methodology version: {version}.",
        "sections": (
            (
                "Sources",
                (
                    "Downloads come from ClickPy, a public ClickHouse service that aggregates the "
                    "PyPI download logs. Data starts on {start} and is read once a day, up to the "
                    "previous day in UTC.",
                    "GitHub stars come from each repository's star history, counted per week. "
                    "Python release and end-of-life dates come from endoflife.date and python.org.",
                ),
            ),
            (
                "What a download is",
                (
                    "A download is a file fetched from PyPI: continuous integration, mirrors and "
                    "bots count the same as a person. Downloads are not users, and total volume "
                    "grows for reasons unrelated to popularity.",
                    "That is why ecopy compares shares instead of raw counts. A library's share is "
                    "its downloads in a month divided by all PyPI downloads that month. The share "
                    "of a category or domain is its downloads divided by those of the whole "
                    "catalog in the same period.",
                ),
            ),
            (
                "The catalog",
                (
                    "About 500 packages: the union of the top 100 of every year since 2017 plus a "
                    "curated list per category. Libraries that were at the top in past years stay "
                    "in the catalog after they fall, so rankings do not show only today's "
                    "survivors.",
                    "Each library has one main category; tags are only for browsing. Renamed "
                    "packages are linked, never added together.",
                ),
            ),
            (
                "Years and rankings",
                (
                    "Years are calendar years in UTC. A year in progress is compared with the same "
                    "dates of the previous year, never with a complete year.",
                    "Movers rank the change in share of the catalog, in percentage points, against "
                    "the previous year. Foundations (packages installed as dependencies of almost "
                    "everything) are left out of movers and newcomers so they do not crowd the "
                    "list.",
                    "Closed years are frozen together with the methodology version that produced "
                    "them. A new version recalculates them; it never edits a frozen year by hand.",
                ),
            ),
            (
                "Python versions",
                (
                    "Version adoption uses closed months only. Shares are calculated over real "
                    "CPython versions; downloads without a version and values that are not a "
                    "version are shown apart.",
                ),
            ),
            (
                "GitHub stars",
                (
                    "Star history is net: it only counts people who still have the star, dated "
                    "when they gave it. Old repositories can show a jump in their first week. "
                    "ecopy stores counts only, never who starred.",
                ),
            ),
            (
                "Updates and corrections",
                (
                    "Data is updated every day and validated before publishing. If validation "
                    "fails, the site keeps the last good data and says so at the top of every "
                    "page.",
                    "Corrections from the source are stored as new files; nothing is overwritten. "
                    "All data and code are public in the repository.",
                ),
            ),
        ),
        "calendar_heading": "Known data problems",
        "calendar_text": (
            "These periods apply to every package. A month without data is a break in the line, "
            "not a zero, and the month in progress is a band with its partial value, never a "
            "projection."
        ),
        "gaps": "Gaps in the source",
        "degraded": (
            "Degraded days: below half of the median of the same weekday in the four previous weeks"
        ),
        "discontinuities": "Discontinuities",
        "discontinuities_text": (
            "Changes in the level of total volume. Growth is not calculated across them, and no "
            "cause is attributed without evidence."
        ),
    },
    "es": {
        "lead": ("De dónde sale cada cifra de ecopy, cómo se calcula y qué no puede decirte."),
        "version": "Versión metodológica vigente: {version}.",
        "sections": (
            (
                "Fuentes",
                (
                    "Las descargas vienen de ClickPy, un servicio público de ClickHouse que agrega "
                    "los registros de descargas de PyPI. Los datos empiezan el {start} y se leen "
                    "una vez por día, hasta el día anterior en UTC.",
                    "Las estrellas de GitHub vienen de la historia de estrellas de cada "
                    "repositorio, contada por semana. Las fechas de lanzamiento y fin de soporte "
                    "de Python vienen de endoflife.date y python.org.",
                ),
            ),
            (
                "Qué es una descarga",
                (
                    "Una descarga es un archivo bajado de PyPI: la integración continua, los "
                    "espejos y los bots cuentan igual que una persona. Las descargas no son "
                    "usuarios, y el volumen total crece por razones ajenas a la popularidad.",
                    "Por eso ecopy compara cuotas y no conteos. La cuota de una librería son sus "
                    "descargas de un mes divididas por todas las descargas de PyPI de ese mes. La "
                    "cuota de una categoría o dominio son sus descargas divididas por las de todo "
                    "el catálogo en el mismo período.",
                ),
            ),
            (
                "El catálogo",
                (
                    "Unos 500 paquetes: la unión del top 100 de cada año desde 2017 más una lista "
                    "curada por categoría. Las librerías que estuvieron arriba en años pasados "
                    "siguen en el catálogo aunque caigan, para que los rankings no muestren solo "
                    "a las sobrevivientes de hoy.",
                    "Cada librería tiene una categoría principal; los tags son solo para navegar. "
                    "Los paquetes renombrados se enlazan, nunca se suman.",
                ),
            ),
            (
                "Años y rankings",
                (
                    "Los años son calendario en UTC. Un año en curso se compara con las mismas "
                    "fechas del año anterior, nunca con un año completo.",
                    "Los movers ordenan el cambio de cuota del catálogo, en puntos, contra el año "
                    "anterior. La infraestructura base (paquetes que se instalan como dependencia "
                    "de casi todo) queda fuera de movers y recién llegados para no tapar la lista.",
                    "Los años cerrados se congelan junto con la versión metodológica que los "
                    "produjo. Una versión nueva los recalcula; nunca se edita un año congelado a "
                    "mano.",
                ),
            ),
            (
                "Versiones de Python",
                (
                    "La adopción de versiones usa solo meses cerrados. Las cuotas se calculan "
                    "sobre versiones reales de CPython; las descargas sin versión y los valores "
                    "que no son una versión se muestran aparte.",
                ),
            ),
            (
                "Estrellas de GitHub",
                (
                    "La historia de estrellas es neta: solo cuenta a quienes conservan la "
                    "estrella, fechada cuando la dieron. Los repositorios viejos pueden mostrar un "
                    "salto en su primera semana. ecopy guarda solo conteos, nunca quién dio la "
                    "estrella.",
                ),
            ),
            (
                "Actualización y correcciones",
                (
                    "Los datos se actualizan todos los días y se validan antes de publicar. Si la "
                    "validación falla, el sitio conserva los últimos datos buenos y lo avisa "
                    "arriba de cada página.",
                    "Las correcciones de la fuente se guardan como archivos nuevos; nada se "
                    "sobrescribe. Todos los datos y el código son públicos en el repositorio.",
                ),
            ),
        ),
        "calendar_heading": "Problemas conocidos de los datos",
        "calendar_text": (
            "Estos períodos valen para todos los paquetes. Un mes sin datos es un corte en la "
            "línea, no un cero, y el mes en curso es una franja con su valor parcial, nunca una "
            "proyección."
        ),
        "gaps": "Huecos de la fuente",
        "degraded": (
            "Días degradados: por debajo de la mitad de la mediana del mismo día de la semana en "
            "las cuatro semanas anteriores"
        ),
        "discontinuities": "Discontinuidades",
        "discontinuities_text": (
            "Cambios de nivel del volumen total. El crecimiento no se calcula a través de ellos y "
            "no se atribuye causa sin evidencia."
        ),
    },
}
