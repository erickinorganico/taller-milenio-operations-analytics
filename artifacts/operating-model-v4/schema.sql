PRAGMA foreign_keys = ON;

CREATE TABLE "customers" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "segment" TEXT NOT NULL CHECK (segment IN ('particular','fleet')),
  "consent" INTEGER NOT NULL CHECK (consent IN (0,1)),
  "contact" TEXT
) STRICT;

CREATE TABLE "vehicles" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "label" TEXT NOT NULL,
  "plate" TEXT NOT NULL,
  "odometer_km" INTEGER NOT NULL CHECK (odometer_km >= 0),
  FOREIGN KEY("customer_id") REFERENCES "customers"(id)
) STRICT;

CREATE TABLE "leads" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "vehicle_id" TEXT,
  "need" TEXT NOT NULL,
  "channel" TEXT NOT NULL,
  "follow_up_at" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK (status IN ('new','qualified','quoted','won','lost')),
  FOREIGN KEY("customer_id") REFERENCES "customers"(id),
  FOREIGN KEY("vehicle_id") REFERENCES "vehicles"(id)
) STRICT;

CREATE TABLE "quotes" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "vehicle_id" TEXT NOT NULL,
  "description" TEXT NOT NULL,
  "amount_cents" INTEGER NOT NULL CHECK (amount_cents >= 0),
  "valid_until" TEXT NOT NULL,
  "authorization_ref" TEXT,
  "status" TEXT NOT NULL CHECK (status IN ('draft','sent','accepted','rejected','expired','cancelled')),
  FOREIGN KEY("customer_id") REFERENCES "customers"(id),
  FOREIGN KEY("vehicle_id") REFERENCES "vehicles"(id)
) STRICT;

CREATE TABLE "appointments" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "vehicle_id" TEXT NOT NULL,
  "starts_at" TEXT NOT NULL,
  "reason" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK (status IN ('pending','confirmed','arrived','no_show','cancelled')),
  FOREIGN KEY("customer_id") REFERENCES "customers"(id),
  FOREIGN KEY("vehicle_id") REFERENCES "vehicles"(id)
) STRICT;

CREATE TABLE "technicians" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "specialty" TEXT NOT NULL
) STRICT;

CREATE TABLE "bays" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "name" TEXT NOT NULL
) STRICT;

CREATE TABLE "work_orders" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "vehicle_id" TEXT NOT NULL,
  "quote_id" TEXT,
  "contract_id" TEXT,
  "technician_id" TEXT,
  "bay_id" TEXT,
  "description" TEXT NOT NULL,
  "due_at" TEXT NOT NULL,
  "opened_at" TEXT NOT NULL,
  "completed_at" TEXT,
  "inspection" TEXT,
  "authorization_ref" TEXT,
  "qc_ref" TEXT,
  "block_reason" TEXT,
  "status" TEXT NOT NULL CHECK (status IN ('received','inspected','authorized','waiting_parts','scheduled','in_service','quality_check','rework','ready','delivered','cancelled')),
  FOREIGN KEY("customer_id") REFERENCES "customers"(id),
  FOREIGN KEY("vehicle_id") REFERENCES "vehicles"(id),
  FOREIGN KEY("quote_id") REFERENCES "quotes"(id),
  FOREIGN KEY("contract_id") REFERENCES "contracts"(id),
  FOREIGN KEY("technician_id") REFERENCES "technicians"(id),
  FOREIGN KEY("bay_id") REFERENCES "bays"(id)
) STRICT;

CREATE TABLE "suppliers" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "contact" TEXT
) STRICT;

CREATE TABLE "parts" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "sku" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "supplier_id" TEXT NOT NULL,
  "unit_cost_cents" INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
  "reorder_point" INTEGER NOT NULL CHECK (reorder_point >= 0),
  FOREIGN KEY("supplier_id") REFERENCES "suppliers"(id)
) STRICT;

CREATE TABLE "purchases" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "part_id" TEXT NOT NULL,
  "quantity" INTEGER NOT NULL CHECK (quantity > 0),
  "unit_cost_cents" INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
  "expected_at" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK (status IN ('draft','ordered','received','cancelled')),
  FOREIGN KEY("part_id") REFERENCES "parts"(id)
) STRICT;

CREATE TABLE "stock_moves" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "part_id" TEXT NOT NULL,
  "work_order_id" TEXT,
  "purchase_id" TEXT,
  "move_type" TEXT NOT NULL CHECK (move_type IN ('receive','consume','return','adjust')),
  "quantity" INTEGER NOT NULL,
  "unit_cost_cents" INTEGER NOT NULL CHECK (unit_cost_cents >= 0),
  "reason" TEXT NOT NULL,
  FOREIGN KEY("part_id") REFERENCES "parts"(id),
  FOREIGN KEY("work_order_id") REFERENCES "work_orders"(id),
  FOREIGN KEY("purchase_id") REFERENCES "purchases"(id)
) STRICT;

CREATE TABLE "reservations" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "part_id" TEXT NOT NULL,
  "work_order_id" TEXT NOT NULL,
  "quantity" INTEGER NOT NULL CHECK (quantity > 0),
  "status" TEXT NOT NULL CHECK (status IN ('reserved','consumed','released')),
  FOREIGN KEY("part_id") REFERENCES "parts"(id),
  FOREIGN KEY("work_order_id") REFERENCES "work_orders"(id)
) STRICT;

CREATE TABLE "fleet_accounts" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "industry" TEXT NOT NULL,
  "fleet_size" INTEGER NOT NULL CHECK (fleet_size > 0),
  "owner" TEXT NOT NULL,
  FOREIGN KEY("customer_id") REFERENCES "customers"(id)
) STRICT;

CREATE TABLE "contacts" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "fleet_account_id" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "role" TEXT NOT NULL,
  "contact" TEXT NOT NULL,
  "consent" INTEGER NOT NULL CHECK (consent IN (0,1)),
  FOREIGN KEY("fleet_account_id") REFERENCES "fleet_accounts"(id)
) STRICT;

CREATE TABLE "opportunities" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "fleet_account_id" TEXT NOT NULL,
  "title" TEXT NOT NULL,
  "value_cents" INTEGER NOT NULL CHECK (value_cents >= 0),
  "next_step" TEXT NOT NULL,
  "follow_up_at" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK (status IN ('research','qualified','proposal','negotiation','won','lost')),
  FOREIGN KEY("fleet_account_id") REFERENCES "fleet_accounts"(id)
) STRICT;

CREATE TABLE "contracts" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "fleet_account_id" TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "sla_hours" INTEGER NOT NULL CHECK (sla_hours > 0),
  "starts_at" TEXT NOT NULL,
  "ends_at" TEXT NOT NULL,
  "approval_ref" TEXT,
  "status" TEXT NOT NULL CHECK (status IN ('draft','active','suspended','expired','cancelled')),
  FOREIGN KEY("fleet_account_id") REFERENCES "fleet_accounts"(id)
) STRICT;

CREATE TABLE "maintenance" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "vehicle_id" TEXT NOT NULL,
  "contract_id" TEXT NOT NULL,
  "service" TEXT NOT NULL,
  "due_at" TEXT NOT NULL,
  "due_km" INTEGER NOT NULL CHECK (due_km >= 0),
  "work_order_id" TEXT,
  "status" TEXT NOT NULL CHECK (status IN ('due','scheduled','completed','cancelled')),
  FOREIGN KEY("vehicle_id") REFERENCES "vehicles"(id),
  FOREIGN KEY("contract_id") REFERENCES "contracts"(id),
  FOREIGN KEY("work_order_id") REFERENCES "work_orders"(id)
) STRICT;

CREATE TABLE "tow_units" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "capability" TEXT NOT NULL
) STRICT;

CREATE TABLE "tows" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "vehicle_id" TEXT NOT NULL,
  "pickup" TEXT NOT NULL,
  "destination" TEXT NOT NULL,
  "conditions" TEXT NOT NULL,
  "requested_at" TEXT NOT NULL,
  "due_at" TEXT NOT NULL,
  "closed_at" TEXT,
  "amount_cents" INTEGER CHECK (amount_cents >= 0),
  "unit_id" TEXT,
  "safety_ref" TEXT,
  "human_approval_ref" TEXT,
  "status" TEXT NOT NULL CHECK (status IN ('requested','assessed','quoted','assigned','accepted','en_route','arrived','transporting','closed','cancelled')),
  FOREIGN KEY("customer_id") REFERENCES "customers"(id),
  FOREIGN KEY("vehicle_id") REFERENCES "vehicles"(id),
  FOREIGN KEY("unit_id") REFERENCES "tow_units"(id)
) STRICT;

CREATE TABLE "invoices" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "customer_id" TEXT NOT NULL,
  "work_order_id" TEXT,
  "tow_id" TEXT,
  "amount_cents" INTEGER NOT NULL CHECK (amount_cents >= 0),
  "due_at" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK (status IN ('draft','issued','void')),
  FOREIGN KEY("customer_id") REFERENCES "customers"(id),
  FOREIGN KEY("work_order_id") REFERENCES "work_orders"(id),
  FOREIGN KEY("tow_id") REFERENCES "tows"(id)
) STRICT;

CREATE TABLE "payments" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "invoice_id" TEXT NOT NULL,
  "amount_cents" INTEGER NOT NULL CHECK (amount_cents > 0),
  "method" TEXT NOT NULL CHECK (method IN ('cash','transfer','card')),
  "reference" TEXT NOT NULL,
  "paid_at" TEXT NOT NULL,
  FOREIGN KEY("invoice_id") REFERENCES "invoices"(id)
) STRICT;

CREATE TABLE "expenses" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "description" TEXT NOT NULL,
  "amount_cents" INTEGER NOT NULL CHECK (amount_cents > 0),
  "category" TEXT NOT NULL CHECK (category IN ('parts','rent','payroll','utilities','other')),
  "method" TEXT NOT NULL CHECK (method IN ('cash','transfer','card')),
  "paid_at" TEXT NOT NULL
) STRICT;

CREATE TABLE "campaigns" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "name" TEXT NOT NULL,
  "audience" TEXT NOT NULL CHECK (audience IN ('particular','fleet')),
  "objective" TEXT NOT NULL,
  "draft" TEXT NOT NULL,
  "status" TEXT NOT NULL CHECK (status IN ('draft','review','approved','archived'))
) STRICT;

CREATE TABLE "proposals" (
  id TEXT PRIMARY KEY NOT NULL,
  version INTEGER NOT NULL CHECK(version > 0),
  synthetic INTEGER NOT NULL CHECK(synthetic=1),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  "agent" TEXT NOT NULL,
  "title" TEXT NOT NULL,
  "rationale" TEXT NOT NULL,
  "evidence" TEXT NOT NULL CHECK (json_valid(evidence)),
  "approval_required" INTEGER NOT NULL CHECK (approval_required IN (0,1)),
  "external_execution" INTEGER NOT NULL CHECK (external_execution IN (0,1)),
  "status" TEXT NOT NULL CHECK (status IN ('pending','approved','rejected')),
  "decision_note" TEXT
) STRICT;

CREATE TABLE lifecycle_events (
      event_id TEXT PRIMARY KEY NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT NOT NULL,
      from_state TEXT NOT NULL, to_state TEXT NOT NULL, at TEXT NOT NULL,
      actor TEXT NOT NULL, process_id TEXT NOT NULL, synthetic INTEGER NOT NULL CHECK(synthetic=1)
    ) STRICT;

CREATE TABLE journey_links (
      id TEXT PRIMARY KEY NOT NULL, lead_id TEXT NOT NULL REFERENCES leads(id),
      quote_id TEXT NOT NULL REFERENCES quotes(id), appointment_id TEXT NOT NULL REFERENCES appointments(id),
      work_order_id TEXT NOT NULL REFERENCES work_orders(id), synthetic INTEGER NOT NULL CHECK(synthetic=1)
    ) STRICT;

CREATE TABLE "mart_service_journey" ("work_order_id" TEXT,"customer_id" TEXT,"segment" TEXT,"vehicle_id" TEXT,"status" TEXT,"opened_at" TEXT,"completed_at" TEXT,"cycle_hours" REAL,"age_hours" REAL,"history_available" INTEGER,"waiting_parts_hours" REAL,"in_service_hours" REAL,"rework_observed" INTEGER,"contract_id" TEXT,"sla_status" TEXT,"invoiced_cents" INTEGER,"paid_cents" INTEGER,"receivable_cents" INTEGER);

CREATE TABLE "mart_receivables" ("invoice_id" TEXT,"customer_id" TEXT,"segment" TEXT,"due_at" TEXT,"invoiced_cents" INTEGER,"paid_cents" INTEGER,"balance_cents" INTEGER,"days_overdue" INTEGER,"aging_bucket" TEXT);

CREATE TABLE "mart_daily_operations" ("day" TEXT,"opened" INTEGER,"delivered" INTEGER,"collected_cents" INTEGER,"expense_cents" INTEGER);

CREATE TABLE "mart_fleet_scorecard" ("fleet_account_id" TEXT,"customer_id" TEXT,"industry" TEXT,"declared_vehicles" INTEGER,"captured_vehicles" INTEGER,"services" INTEGER,"eligible_delivered" INTEGER,"sla_met" INTEGER,"sla_breached" INTEGER,"sla_unknown" INTEGER,"cycle_p90_hours" REAL,"pipeline_cents" INTEGER,"receivable_cents" INTEGER);

CREATE TABLE "mart_inventory" ("part_id" TEXT,"name" TEXT,"on_hand" INTEGER,"reserved" INTEGER,"available" INTEGER,"reorder_point" INTEGER,"net_consumed_cost_cents" INTEGER);

CREATE TABLE "mart_process_waits" ("entity_type" TEXT,"stage" TEXT,"intervals" INTEGER,"cases" INTEGER,"total_hours" REAL,"mean_interval_hours" REAL);

CREATE INDEX "idx_vehicles_customer_id" ON "vehicles"("customer_id");

CREATE INDEX "idx_leads_customer_id" ON "leads"("customer_id");

CREATE INDEX "idx_leads_vehicle_id" ON "leads"("vehicle_id");

CREATE INDEX "idx_quotes_customer_id" ON "quotes"("customer_id");

CREATE INDEX "idx_quotes_vehicle_id" ON "quotes"("vehicle_id");

CREATE INDEX "idx_appointments_customer_id" ON "appointments"("customer_id");

CREATE INDEX "idx_appointments_vehicle_id" ON "appointments"("vehicle_id");

CREATE INDEX "idx_work_orders_customer_id" ON "work_orders"("customer_id");

CREATE INDEX "idx_work_orders_vehicle_id" ON "work_orders"("vehicle_id");

CREATE INDEX "idx_work_orders_quote_id" ON "work_orders"("quote_id");

CREATE INDEX "idx_work_orders_contract_id" ON "work_orders"("contract_id");

CREATE INDEX "idx_work_orders_technician_id" ON "work_orders"("technician_id");

CREATE INDEX "idx_work_orders_bay_id" ON "work_orders"("bay_id");

CREATE INDEX "idx_parts_supplier_id" ON "parts"("supplier_id");

CREATE INDEX "idx_purchases_part_id" ON "purchases"("part_id");

CREATE INDEX "idx_stock_moves_part_id" ON "stock_moves"("part_id");

CREATE INDEX "idx_stock_moves_work_order_id" ON "stock_moves"("work_order_id");

CREATE INDEX "idx_stock_moves_purchase_id" ON "stock_moves"("purchase_id");

CREATE INDEX "idx_reservations_part_id" ON "reservations"("part_id");

CREATE INDEX "idx_reservations_work_order_id" ON "reservations"("work_order_id");

CREATE INDEX "idx_fleet_accounts_customer_id" ON "fleet_accounts"("customer_id");

CREATE INDEX "idx_contacts_fleet_account_id" ON "contacts"("fleet_account_id");

CREATE INDEX "idx_opportunities_fleet_account_id" ON "opportunities"("fleet_account_id");

CREATE INDEX "idx_contracts_fleet_account_id" ON "contracts"("fleet_account_id");

CREATE INDEX "idx_maintenance_vehicle_id" ON "maintenance"("vehicle_id");

CREATE INDEX "idx_maintenance_contract_id" ON "maintenance"("contract_id");

CREATE INDEX "idx_maintenance_work_order_id" ON "maintenance"("work_order_id");

CREATE INDEX "idx_tows_customer_id" ON "tows"("customer_id");

CREATE INDEX "idx_tows_vehicle_id" ON "tows"("vehicle_id");

CREATE INDEX "idx_tows_unit_id" ON "tows"("unit_id");

CREATE INDEX "idx_invoices_customer_id" ON "invoices"("customer_id");

CREATE INDEX "idx_invoices_work_order_id" ON "invoices"("work_order_id");

CREATE INDEX "idx_invoices_tow_id" ON "invoices"("tow_id");

CREATE INDEX "idx_payments_invoice_id" ON "payments"("invoice_id");

CREATE INDEX idx_lifecycle_entity ON lifecycle_events(entity_type, entity_id, at);

CREATE INDEX idx_lifecycle_at ON lifecycle_events(at);
