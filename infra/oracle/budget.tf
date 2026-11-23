# Red de seguridad de costos: si la cuenta llega a gastar 1 USD en un mes, llega un
# correo. Con todo dentro de Always Free el gasto debe ser 0; esta alerta detecta un
# error (p. ej. un recurso de pago creado por accidente) antes de que sea caro.
# Los presupuestos de OCI son gratuitos.

resource "oci_budget_budget" "guardrail" {
  compartment_id = var.tenancy_ocid
  display_name   = "${var.project}-guardrail"
  description    = "Alerta si el gasto mensual supera 1 USD"
  amount         = 1
  reset_period   = "MONTHLY"
  target_type    = "COMPARTMENT"
  targets        = [var.tenancy_ocid]
  freeform_tags  = local.tags
}

resource "oci_budget_alert_rule" "any_spend" {
  budget_id      = oci_budget_budget.guardrail.id
  display_name   = "gasto-real-1usd"
  type           = "ACTUAL"
  threshold      = 100 # % del presupuesto (100 % de 1 USD)
  threshold_type = "PERCENTAGE"
  recipients     = var.budget_alert_email
  message        = "PanaStatus: la cuenta de Oracle Cloud registra gasto real. Revisa qué recurso no es Always Free."
}
