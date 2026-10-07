"""Explain the active stage without bypassing any domain transition guards."""
from .access import can

STEPS = {
    "intake": ("Iniciar la inspección", "Asigna responsable y fecha prometida; avanza a Inspección para documentar lo encontrado.", "overview", "work"),
    "inspection": ("Documentar y cotizar", "Registra los puntos revisados y sus fotos. Después prepara el presupuesto y pásalo a autorización.", "inspection", "work"),
    "awaiting_approval": ("Registrar respuesta del cliente", "Comprueba el presupuesto presentado y registra quién autoriza con su referencia. La foto de una hoja no sustituye esa autorización.", "quote", "reception"),
    "approved": ("Preparar el trabajo", "Reserva las refacciones necesarias y avanza a En trabajo cuando esté listo el equipo.", "parts", "stock"),
    "in_progress": ("Registrar trabajo y revisar calidad", "Captura los tiempos y consumos. Cuando termine la reparación, avanza a Control de calidad.", "work", "work"),
    "waiting_parts": ("Resolver el bloqueo de refacciones", "Revisa qué pieza falta y su recepción. Al recibirla, retoma el trabajo y registra los movimientos.", "parts", "stock"),
    "quality": ("Registrar la revisión de calidad", "Una revisión aprobada permite marcar la orden lista. Si falla, vuelve al trabajo y repite la comprobación.", "work", "work"),
    "ready": ("Coordinar la entrega", "Comprueba que no queden reservas pendientes y registra la entrega al cliente.", "overview", "reception"),
    "delivered": ("Revisar comprobante y saldo", "Administración emite el comprobante y registra los cobros. Consulta el saldo y conserva sus referencias.", "payment", "finance_read"),
    "cancelled": ("Consultar el historial", "La orden está cancelada. Consulta el motivo y los movimientos en la bitácora.", "history", "orders_read_all"),
}


def guidance(order, user):
    title, description, anchor, capability = STEPS[order.status]
    allowed = can(user, capability)
    return {"title": title, "description": description, "anchor": anchor if allowed else "overview",
            "action": "Ir al paso" if allowed else "Ver responsable y seguimiento"}
