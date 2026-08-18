# Regla de EventBridge para la ejecución programada (Cron)
resource "aws_cloudwatch_event_rule" "daily_audit_rule" {
  name                = "finops_daily_audit_rule_${var.environment}"
  description         = "Regla programada para ejecutar la auditoria de FinOps diariamente"
  schedule_expression = var.schedule_expression

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Target de la regla de EventBridge apuntando a la función Lambda
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.daily_audit_rule.name
  target_id = "FinOpsLambdaTarget"
  arn       = aws_lambda_function.finops_auditor.arn
}

# Permiso explícito para que EventBridge invoque la función Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.finops_auditor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_audit_rule.arn
}
