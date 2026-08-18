variable "aws_region" {
  description = "Región de AWS donde se desplegarán los recursos"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Entorno de despliegue (dev, prod, test)"
  type        = string
  default     = "prod"
}

variable "webhook_url" {
  description = "URL del Webhook de Discord/Slack para notificaciones (sensible)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "schedule_expression" {
  description = "Expresión Cron o Rate de EventBridge para la ejecución automática"
  type        = string
  default     = "cron(0 8 * * ? *)" # Todos los días a las 08:00 AM UTC
}

variable "required_tags" {
  description = "Lista separada por comas de etiquetas EC2 obligatorias"
  type        = string
  default     = "Owner,Environment"
}
