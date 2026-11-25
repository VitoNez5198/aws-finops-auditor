resource "aws_ssm_parameter" "webhook_url" {
  name        = "/finops-auditor/${var.environment}/webhook-url"
  description = "URL del webhook de Discord/Slack para el reporte diario de FinOps"
  type        = "SecureString"
  value       = var.webhook_url != "" ? var.webhook_url : "no-configurado"

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
