data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../src"
  output_path = "${path.module}/lambda_payload.zip"
}

resource "aws_cloudwatch_log_group" "finops_logs" {
  name              = "/aws/lambda/finops_auditor_${var.environment}"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

resource "aws_lambda_function" "finops_auditor" {
  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256
  function_name    = "finops_auditor_${var.environment}"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      WEBHOOK_SSM_PARAM = aws_ssm_parameter.webhook_url.name
      REQUIRED_TAGS     = var.required_tags
    }
  }

  depends_on = [
    aws_iam_role_policy_attachment.attach_finops_policy,
    aws_cloudwatch_log_group.finops_logs,
  ]

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}
