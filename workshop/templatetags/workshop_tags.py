from decimal import Decimal, InvalidOperation
from django import template
register = template.Library()

@register.filter
def money(value):
    if value is None or value == "":
        return "Sin datos"
    try:
        return f"${Decimal(str(value)):,.2f}"
    except (InvalidOperation, ValueError):
        return str(value)

@register.filter
def get(mapping, key):
    return mapping.get(key, "") if isinstance(mapping, dict) else getattr(mapping, key, "")

@register.filter
def status_label(value):
    actions = {"photo_sourced":"Servicio de foto agregado al presupuesto", "created":"Registro creado",
               "image_created":"Registro creado desde foto", "image_updated":"Registro actualizado desde foto"}
    if str(value) in actions:
        return actions[str(value)]
    return {"periodic":"Por intervalo", "events":"Por cambios del taller", "manual":"Solicitada por el equipo", "native":"Codex nativo", "intake":"Recepción", "inspection":"Inspección", "awaiting_approval":"Por autorizar", "approved":"Autorizado", "in_progress":"En trabajo", "waiting_parts":"Espera refacciones", "quality":"Control de calidad", "ready":"Listo para entregar", "delivered":"Entregado", "cancelled":"Cancelado", "draft":"Borrador", "sent":"Enviado a revisión", "rejected":"Rechazado", "superseded":"Sustituido", "scheduled":"Programado", "confirmed":"Confirmado", "completed":"Completado", "active":"Activo", "expired":"Vencido", "individual":"Particular", "fleet":"Flotilla", "ordered":"Pedido", "partial":"Parcial", "received":"Recibido", "requested":"Solicitado", "assigned":"Asignado", "en_route":"En camino", "arrived":"En sitio", "pending":"Pendiente", "accepted":"Aceptado", "stale":"Datos cambiaron", "open":"Abierto", "dismissed":"Descartado", "pass":"Aprobado", "fail":"No aprobado", "okay":"Correcto", "watch":"Revisar", "urgent":"Atención", "rules":"Reglas verificables", "native_codex":"Modelo Codex", "success":"Completado", "succeeded":"Completado", "failed":"Falló", "blocked":"Bloqueado", "running":"En curso", "known":"Disponible", "unknown":"Sin datos suficientes", "available":"Disponible", "labor":"Mano de obra", "part":"Refacción", "service":"Servicio", "operations":"Operación", "collections":"Cobranza", "data_quality":"Calidad de datos"}.get(str(value),value)
