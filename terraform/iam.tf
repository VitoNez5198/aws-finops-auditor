# Rol de IAM para la ejecución de AWS Lambda usando name_prefix para evitar colisiones
resource "aws_iam_role" "lambda_exec_role" {
  name_prefix = "finops-lambda-role-"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    ManagedBy   = "Terraform"
  }
}

# Política IAM con principio de menor privilegio (Least Privilege)
resource "aws_iam_policy" "lambda_finops_policy" {
  name_prefix = "finops-policy-"
  description = "Permisos de lectura para auditoria de EC2, Cost Explorer y escritura en CloudWatch Logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # Permisos para CloudWatch Logs
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      # Permisos de solo lectura para EC2
      {
        Effect = "Allow"
        Action = [
          "ec2:DescribeInstances",
          "ec2:DescribeTags"
        ]
        Resource = "*"
      },
      # Permisos de solo lectura para Cost Explorer
      {
        Effect = "Allow"
        Action = [
          "ce:GetCostAndUsage"
        ]
        Resource = "*"
      }
    ]
  })
}

# Vinculación del Rol con la Política
resource "aws_iam_role_policy_attachment" "attach_finops_policy" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_finops_policy.arn
}
