output "lambda_function_name" {
  description = "Nombre de la función Lambda aprovisionada"
  value       = aws_lambda_function.finops_auditor.function_name
}

output "lambda_function_arn" {
  description = "ARN de la función Lambda"
  value       = aws_lambda_function.finops_auditor.arn
}

output "eventbridge_rule_arn" {
  description = "ARN de la regla de EventBridge programada"
  value       = aws_cloudwatch_event_rule.daily_audit_rule.arn
}
