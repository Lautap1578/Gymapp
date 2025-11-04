"""
Archivo de constantes globales para la app Gymapp.
Centraliza los slugs, nombres visibles y mapeos de tipos de rutina.

Objetivo:
- Evitar inconsistencias entre views, models y templates.
- Permitir actualizar nombres visibles desde un solo lugar.
"""

# Slugs de rutinas y nombres legibles
RUTINA_SLUGS = {
    "hipertrofia": "Hipertrofia",
    "acondicionamiento": "Acondicionamiento físico",
    "deportista": "Deportista avanzado",
    "fuerza_base": "Fuerza base",
    "edad_temprana": "Edad temprana",
}

# Lista para usar en models.py (choices de Rutina)
RUTINA_CHOICES = [(slug, name) for slug, name in RUTINA_SLUGS.items()]

# Helper (por si se usa en templates o lógica)
def get_rutina_nombre(slug: str) -> str:
    """
    Devuelve el nombre legible de una rutina dado su slug.
    Si no existe, devuelve el slug capitalizado como fallback.
    """
    if not slug:
        return ""
    return RUTINA_SLUGS.get(slug, slug.replace("_", " ").capitalize())

# Ejemplo de uso en otros archivos:
# ---------------------------------
# from gymapp.constants import RUTINA_CHOICES, get_rutina_nombre
#
# class Rutina(models.Model):
#     estructura = models.CharField(max_length=50, choices=RUTINA_CHOICES)
#
# nombre_mostrado = get_rutina_nombre(rutina.estructura)
