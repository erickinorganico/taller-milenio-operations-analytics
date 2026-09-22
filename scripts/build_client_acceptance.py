"""Build a blank, client-facing acceptance workbook.

The workbook is deliberately a human capture surface. It contains no client
names, example approvals, formulas, or inferred values. Use ``--output`` to
choose a new path; existing files are never replaced.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import xlsxwriter


NAVY = "#17324D"
TEAL = "#2A6F78"
INK = "#243746"
MUTED = "#5B6B73"
PAPER = "#F5F7F8"
PALE_BLUE = "#E8F0F3"
PALE_TEAL = "#E4F0EF"
PALE_AMBER = "#FFF4D6"
WHITE = "#FFFFFF"
LINE = "#C9D5D9"


def _blank(ws, row: int, col: int, cell_format) -> None:
    ws.write_blank(row, col, None, cell_format)


def _write(ws, row: int, col: int, value, cell_format) -> None:
    if value is None or value == "":
        _blank(ws, row, col, cell_format)
    else:
        ws.write(row, col, value, cell_format)


def _title(ws, title: str, subtitle: str, last_col: int, formats: dict) -> None:
    ws.merge_range(0, 0, 0, last_col, title, formats["title"])
    ws.merge_range(1, 0, 1, last_col, subtitle, formats["subtitle"])
    ws.set_row(0, 30)
    ws.set_row(1, 38)
    ws.hide_gridlines(2)
    ws.set_tab_color(TEAL)


def _table(
    ws,
    start_row: int,
    headers: list[str],
    rows: list[list[object]],
    table_name: str,
    formats: dict,
) -> tuple[int, int]:
    header_row = start_row
    for col, header in enumerate(headers):
        _write(ws, header_row, col, header, formats["header"])
    for row_offset, values in enumerate(rows, start=1):
        for col, value in enumerate(values):
            _write(ws, start_row + row_offset, col, value, formats["cell"])
    end_row = start_row + len(rows)
    ws.add_table(
        start_row,
        0,
        end_row,
        len(headers) - 1,
        {
            "name": table_name,
            "style": "Table Style Medium 2",
            "columns": [{"header": header} for header in headers],
        },
    )
    return start_row + 1, end_row


def _make_formats(book: xlsxwriter.Workbook) -> dict:
    return {
        "title": book.add_format(
            {"bold": True, "font_name": "Aptos Display", "font_size": 18, "font_color": NAVY, "bg_color": WHITE, "align": "left", "valign": "vcenter"}
        ),
        "subtitle": book.add_format(
            {"font_name": "Aptos", "font_size": 10, "font_color": MUTED, "bg_color": WHITE, "text_wrap": True, "valign": "vcenter"}
        ),
        "section": book.add_format(
            {"bold": True, "font_name": "Aptos", "font_size": 11, "font_color": NAVY, "bg_color": PALE_BLUE, "text_wrap": True, "valign": "vcenter"}
        ),
        "header": book.add_format(
            {"bold": True, "font_name": "Aptos", "font_color": WHITE, "bg_color": NAVY, "text_wrap": True, "valign": "vcenter", "border": 0}
        ),
        "label": book.add_format(
            {"bold": True, "font_name": "Aptos", "font_color": INK, "bg_color": PALE_BLUE, "text_wrap": True, "valign": "top", "border": 1, "border_color": LINE}
        ),
        "cell": book.add_format(
            {"font_name": "Aptos", "font_color": INK, "bg_color": WHITE, "text_wrap": True, "valign": "top", "border": 1, "border_color": LINE}
        ),
        "input": book.add_format(
            {"font_name": "Aptos", "font_color": INK, "bg_color": PALE_AMBER, "text_wrap": True, "valign": "top", "border": 1, "border_color": LINE}
        ),
        "status": book.add_format(
            {"font_name": "Aptos", "font_color": INK, "bg_color": PALE_TEAL, "text_wrap": True, "valign": "top", "border": 1, "border_color": LINE}
        ),
        "note": book.add_format(
            {"font_name": "Aptos", "font_size": 9, "font_color": MUTED, "bg_color": PAPER, "text_wrap": True, "valign": "top", "border": 1, "border_color": LINE}
        ),
        "blank_input": book.add_format(
            {"font_name": "Aptos", "font_color": INK, "bg_color": PALE_AMBER, "text_wrap": True, "valign": "top", "border": 1, "border_color": LINE}
        ),
    }


def _build_scope(book: xlsxwriter.Workbook, formats: dict) -> None:
    ws = book.add_worksheet("ALCANCE")
    _title(ws, "Acuerdo de entrega · Alcance", "Complete los campos amarillos con el cliente. No hay nombres, aprobaciones ni decisiones precargadas.", 3, formats)
    ws.freeze_panes(4, 1)
    ws.set_column("A:A", 28)
    ws.set_column("B:B", 38)
    ws.set_column("C:C", 58)
    ws.set_column("D:D", 30)

    headers = ["Campo", "Valor a completar", "Cómo usarlo", "Referencia / evidencia"]
    fields = [
        ["Negocio", None, "Nombre del negocio o unidad incluida; no agregue nombres personales.", None],
        ["Sponsor", None, "Persona que confirma alcance y preguntas; completar durante la sesión.", None],
        ["Owner del cliente", None, "Responsable del lado cliente para coordinar la revisión.", None],
        ["Analista", None, "Persona que prepara o entrega esta corrida.", None],
        ["Fecha de corte (ISO-8601)", None, "Use una fecha/hora explícita con zona, por ejemplo 2026-09-22T18:00:00Z.", None],
        ["Zona horaria", None, "Zona usada para interpretar fechas del extracto.", None],
        ["Acceso acordado", None, "Describa ubicación, personas autorizadas y forma de compartir la copia.", None],
        ["Retención / eliminación", None, "Indique plazo, responsable y forma de eliminar la copia.", None],
        ["Criterio de aceptación", None, "Controles, preguntas respondidas y límites que el cliente revisará.", None],
    ]
    first, last = _table(ws, 3, headers, fields, "AlcanceCampos", formats)
    for row in range(first, last + 1):
        _blank(ws, row, 1, formats["blank_input"])
        _blank(ws, row, 3, formats["blank_input"])
    ws.set_row(3, 30)
    for row in range(first, last + 1):
        ws.set_row(row, 34)
    ws.data_validation(first, 1, last, 1, {"validate": "text length", "criteria": "between", "minimum": 0, "maximum": 500, "input_title": "Captura humana", "input_message": "Complete con información acordada.", "error_title": "Texto demasiado largo", "error_message": "Use hasta 500 caracteres."})
    ws.data_validation(first + 5, 1, first + 5, 1, {"validate": "list", "source": ["UTC", "America/Tijuana", "America/Mexico_City", "America/Monterrey"], "ignore_blank": True, "input_title": "Zona horaria", "input_message": "Seleccione una zona o escriba la declarada por el cliente."})

    section_row = last + 2
    ws.merge_range(section_row, 0, section_row, 3, "Tres preguntas prioritarias y módulos", formats["section"])
    question_headers = ["Pregunta prioritaria", "Texto a completar", "Por qué importa", "Referencia / evidencia"]
    questions = [[f"Pregunta prioritaria {i}", None, None, None] for i in range(1, 4)]
    q_first, q_last = _table(ws, section_row + 1, question_headers, questions, "PreguntasPrioritarias", formats)
    for row in range(q_first, q_last + 1):
        _blank(ws, row, 1, formats["blank_input"])
        _blank(ws, row, 2, formats["blank_input"])
        _blank(ws, row, 3, formats["blank_input"])
        ws.set_row(row, 36)

    module_row = q_last + 2
    module_headers = ["Módulo / dataset", "Incluido", "Notas de alcance", "Referencia"]
    modules = [[name, None, None, None] for name in ("Ordenes", "Facturas", "Pagos", "Inventario")]
    m_first, m_last = _table(ws, module_row, module_headers, modules, "ModulosAlcance", formats)
    for row in range(m_first, m_last + 1):
        _blank(ws, row, 1, formats["status"])
        _blank(ws, row, 2, formats["blank_input"])
        _blank(ws, row, 3, formats["blank_input"])
        ws.set_row(row, 32)
    ws.data_validation(m_first, 1, m_last, 1, {"validate": "list", "source": ["Pendiente", "Sí", "No"], "ignore_blank": True, "input_title": "Alcance", "input_message": "Marque el alcance acordado."})


def _build_sources(book: xlsxwriter.Workbook, formats: dict) -> None:
    ws = book.add_worksheet("FUENTES")
    _title(ws, "Acuerdo de entrega · Fuentes", "Una fila por dataset. Complete fuente, owner, periodo, conteo, control total, cobertura y autorización con evidencia del cliente.", 9, formats)
    ws.freeze_panes(4, 1)
    widths = [18, 28, 24, 22, 16, 34, 26, 30, 20, 28]
    for col, width in enumerate(widths):
        ws.set_column(col, col, width)
    headers = [
        "Dataset",
        "Fuente / archivo",
        "Owner de fuente",
        "Periodo",
        "Filas / conteo",
        "Control total / definición",
        "Cobertura conocida",
        "Desconocido / faltante",
        "Extracto autorizado",
        "Referencia",
    ]
    rows = [[name, None, None, None, None, None, None, None, None, None] for name in ("Ordenes", "Facturas", "Pagos", "Inventario")]
    first, last = _table(ws, 3, headers, rows, "FuentesDatos", formats)
    for row in range(first, last + 1):
        for col in range(1, 10):
            _blank(ws, row, col, formats["blank_input"] if col != 8 else formats["status"])
        ws.set_row(row, 44)
    ws.data_validation(first, 8, last, 8, {"validate": "list", "source": ["Pendiente", "Sí", "No"], "ignore_blank": True, "input_title": "Autorización", "input_message": "Confirme el extracto con el cliente."})
    ws.data_validation(first, 6, last, 6, {"validate": "list", "source": ["Completa", "Parcial", "Desconocida"], "ignore_blank": True, "input_title": "Cobertura", "input_message": "Describa la cobertura observada."})


def _build_acceptance(book: xlsxwriter.Workbook, formats: dict) -> None:
    ws = book.add_worksheet("ACEPTACION")
    _title(ws, "Acuerdo de entrega · Aceptación", "Todos los controles comienzan en Pendiente. El revisor, la fecha, el resultado y las notas quedan para una persona real.", 6, formats)
    ws.freeze_panes(4, 2)
    widths = [64, 30, 18, 24, 16, 24, 42]
    for col, width in enumerate(widths):
        ws.set_column(col, col, width)
    headers = ["Control técnico o de uso", "Evidencia / referencia", "Estado", "Revisor", "Fecha", "Resultado", "Notas"]
    controls = [
        "La entrada conserva Config, Instrucciones, Ordenes, Facturas, Pagos e Inventario.",
        "Config declara business_name, as_of, snapshot_id y synthetic.",
        "La validación técnica cubre estructura, IDs, tipos, estados, fechas y referencias.",
        "Los importes MXN conservan centavos y los pagos se reconcilian con facturas.",
        "Gerencia.xlsx permite ubicar fuente, registro, campo, snapshot y limitaciones.",
        "Seguimiento.xlsx conserva origen y deja editables solo las anotaciones humanas.",
        "El cliente puede identificar sus tres decisiones prioritarias en la primera lectura.",
        "El cliente puede asignar owner y registrar status, target_date, note y outcome_evidence.",
        "La comparación semanal conserva los registros ausentes como pendientes de verificar.",
        "El paquete no certifica información fiscal ni aprueba acciones de negocio.",
    ]
    rows = [[control, None, "Pendiente", None, None, None, None] for control in controls]
    first, last = _table(ws, 3, headers, rows, "ControlesAceptacion", formats)
    for row in range(first, last + 1):
        _blank(ws, row, 1, formats["blank_input"])
        _write(ws, row, 2, "Pendiente", formats["status"])
        for col in range(3, 7):
            _blank(ws, row, col, formats["blank_input"])
        ws.set_row(row, 42)
    ws.data_validation(first, 2, last, 2, {"validate": "list", "source": ["Pendiente", "Aceptado", "Requiere corrección", "No aplica"], "input_title": "Estado del control", "input_message": "La persona revisora debe actualizar este estado.", "error_title": "Estado inválido", "error_message": "Seleccione un valor de la lista."})


def _build_meetings(book: xlsxwriter.Workbook, formats: dict) -> None:
    ws = book.add_worksheet("REUNIONES")
    _title(ws, "Acuerdo de entrega · Reuniones", "Registre cada reunión semanal después de celebrarla. Las filas están vacías para evitar atribuciones o decisiones ficticias.", 7, formats)
    ws.freeze_panes(4, 0)
    widths = [18, 34, 32, 32, 32, 20, 30, 40]
    for col, width in enumerate(widths):
        ws.set_column(col, col, width)
    headers = ["Fecha", "Participantes", "Decisión 1", "Decisión 2", "Decisión 3", "Próxima revisión", "Referencia de evidencia", "Notas / pendientes"]
    rows = [[None] * len(headers) for _ in range(6)]
    first, last = _table(ws, 3, headers, rows, "RegistroReuniones", formats)
    for row in range(first, last + 1):
        for col in range(len(headers)):
            _blank(ws, row, col, formats["blank_input"])
        ws.set_row(row, 52)
    ws.data_validation(first, 0, last, 0, {"validate": "text length", "criteria": "between", "minimum": 0, "maximum": 40, "ignore_blank": True, "input_title": "Fecha", "input_message": "Use fecha o fecha/hora declarada por el cliente."})


def build(output: str | Path) -> Path:
    target = Path(output)
    if target.exists():
        raise FileExistsError(f"La salida ya existe; use otra ruta: {target}")
    if target.suffix.lower() != ".xlsx":
        raise ValueError("La salida debe tener extensión .xlsx")
    target.parent.mkdir(parents=True, exist_ok=True)
    book = xlsxwriter.Workbook(str(target), {"strings_to_formulas": False, "strings_to_urls": False})
    book.set_properties(
        {
            "title": "Milenio · Acuerdo de entrega",
            "subject": "Plantilla humana de alcance, fuentes, aceptación y reuniones",
            "author": "Milenio",
            "comments": "Plantilla vacía; no contiene datos de personas ni aprobaciones precargadas.",
        }
    )
    formats = _make_formats(book)
    _build_scope(book, formats)
    _build_sources(book, formats)
    _build_acceptance(book, formats)
    _build_meetings(book, formats)
    book.close()
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="Ruta nueva del archivo .xlsx")
    args = parser.parse_args()
    try:
        print(build(args.output))
        return 0
    except (FileExistsError, OSError, ValueError) as exc:
        parser.error(str(exc))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
