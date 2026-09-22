-- MXN integer cents. Quotes are intentionally excluded from invoiced/paid.
WITH billed AS (
  SELECT COALESCE(SUM(amount_cents),0) AS invoiced_cents FROM v_invoices WHERE status='issued'
), paid AS (
  SELECT COALESCE(SUM(amount_cents),0) AS paid_cents,
         COALESCE(SUM(CASE WHEN method='cash' THEN amount_cents ELSE 0 END),0) AS cash_in_cents
  FROM v_payments
), expenses AS (
  SELECT COALESCE(SUM(amount_cents),0) AS expenses_cents,
         COALESCE(SUM(CASE WHEN method='cash' THEN amount_cents ELSE 0 END),0) AS cash_out_cents
  FROM v_expenses
)
SELECT invoiced_cents, paid_cents, invoiced_cents-paid_cents AS receivable_cents,
       cash_in_cents-cash_out_cents AS cash_net_cents, expenses_cents
FROM billed CROSS JOIN paid CROSS JOIN expenses;
