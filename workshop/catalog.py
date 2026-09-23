"""Explicit public data surfaces; auth/session tables are never exposed."""
from . import models as m

CATALOG = {
 "customers":(m.Customer,"Clientes",["name","phone","email","kind","notes"],"reception"),
 "vehicles":(m.Vehicle,"Vehículos",["customer","plate","vin","make","model","year","odometer"],"reception"),
 "appointments":(m.Appointment,"Agenda de citas",["vehicle","scheduled_at","reason","status"],"reception"),
 "parts":(m.Part,"Catálogo de refacciones",["sku","name","unit","cost","sale_price","reorder_point"],"stock"),
 "suppliers":(m.Supplier,"Proveedores",["name","phone","email"],"stock"),
 "purchases":(m.PurchaseOrder,"Órdenes de compra",["supplier","number","status"],"stock"),
 "contracts":(m.FleetContract,"Contratos de flotilla",["customer","name","start_date","end_date","monthly_fee","sla_hours","status"],"reception"),
 "maintenance":(m.MaintenancePlan,"Mantenimiento programado",["vehicle","description","due_date","due_odometer","status","work_order"],"reception"),
}
SOURCE_MODELS = {"customers":m.Customer,"vehicles":m.Vehicle,"appointments":m.Appointment,"orders":m.WorkOrder,"inspections":m.Inspection,"quotes":m.Quote,"quote-lines":m.QuoteLine,"parts":m.Part,"stock":m.StockMovement,"reservations":m.Reservation,"suppliers":m.Supplier,"purchases":m.PurchaseOrder,"purchase-lines":m.PurchaseLine,"time":m.TimeEntry,"quality":m.QualityCheck,"invoices":m.Invoice,"payments":m.Payment,"contracts":m.FleetContract,"maintenance":m.MaintenancePlan,"tows":m.TowService,"agent-runs":m.AgentRun,"proposals":m.Proposal,"tasks":m.ActionTask,"audit":m.AuditEvent}
SOURCE_TITLES = {"customers":"Clientes","vehicles":"Vehículos","appointments":"Citas","orders":"Órdenes","inspections":"Inspecciones","quotes":"Cotizaciones","quote-lines":"Conceptos cotizados","parts":"Refacciones","stock":"Movimientos de inventario","reservations":"Reservas de refacciones","suppliers":"Proveedores","purchases":"Compras","purchase-lines":"Partidas de compra","time":"Tiempos de trabajo","quality":"Control de calidad","invoices":"Comprobantes administrativos","payments":"Pagos","contracts":"Contratos de flotilla","maintenance":"Mantenimiento programado","tows":"Servicios de grúa","agent-runs":"Ejecuciones de agentes","proposals":"Propuestas","tasks":"Acciones de seguimiento","audit":"Bitácora de cambios"}
