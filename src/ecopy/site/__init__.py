"""Sitio estático: recibe modelos de vista y escribe HTML; nunca toca el store."""

from ecopy.site.render import render_site

__all__ = ["render_site"]
