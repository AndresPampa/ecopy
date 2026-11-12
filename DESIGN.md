# Design — ecopy

Dirección **Estratos** (Etapa 4). Los valores están en `src/ecopy/site/static/site.css`; la razón y
la evidencia, en `docs/design/etapa-4-librerias-y-comparador.md`.

## Idea

El dato es la interfaz: la portada es la cuota por dominio, año por año, y cada columna abre su año.

## Color

- Claro y oscuro son selecciones separadas, no una inversión.
- Cada dominio tiene un color fijo en todo el sitio (`--d-*`). El orden naranja, violeta, aqua, amarillo
  y azul está validado con `validate_palette.js`: cambiarlo exige validar de nuevo.
- Datos e IA lleva el color cálido y va sobre la base, porque es el dominio que cuenta la historia.
- El color sigue a la entidad: en el comparador, una librería conserva su color al quitar otra.

## Tema

Pythoneer es el tema claro y Pythonista el oscuro. Sin elección guardada manda el sistema operativo.
El botón nombra el tema al que cambia y su punto usa la tinta del tema actual.

## Marca

"eco-py" en la tipografía del sitio; el guion es una serpiente de un solo trazo, en tinta, con el ojo del
color de Datos e IA. Ondula como una serie de datos. Va inline en `_base.html` con clases, sin `style`.
El favicon es la misma serpiente sobre una placa oscura, con colores fijos y sin `<style>` propio.

## Tipografía

Fuentes del sistema. Monoespaciada solo para nombres de paquete, que son código.

## Gráficos

- Los porcentajes y los puntos de cuota llevan 3 decimales: con menos, las cuotas chicas salían 0,0 %.
- Sin doble eje. Sin puntos en cada dato. Líneas de 2 px y rejilla tenue.
- El mes en curso nunca se dibuja como punto de la línea: es una franja con su texto.
- Las discontinuidades son una línea vertical rotulada, sin atribuirles causa.
- Sparklines: cuota de PyPI, 36 meses cerrados, escala propia y la magnitud al lado.
- SVG generado en Python con atributos y clases; ECharts para lo interactivo. Nada inline.
