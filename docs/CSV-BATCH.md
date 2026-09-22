# Carga de snapshot CSV

Un snapshot contiene **los 25** archivos `<entidad>.csv`, incluso para tablas vacías (solo encabezado). Exporte CSV UTF-8 desde Excel o Sheets; no se leen rutas externas ni se modifica el origen.

```powershell
python -c "from milenio.snapshot_io import load_snapshot; load_snapshot('C:\ruta\snapshot')"
```

Cada archivo requiere `id`, todos los campos de `FIELDS` y `synthetic`; las columnas opcionales son `version`, `created_at`, `updated_at`. Si faltan metadatos, se asignan versión 1 y el corte DEMO_NOW: esto es metadato de captura, **no reconstruye historia observada**. Solo se permite `synthetic=true`; se rechazan fórmulas, floats, joins inválidos, tablas ausentes y archivos mayores a 1 MB.
