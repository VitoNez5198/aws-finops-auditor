import json
import logging
import os
from ec2_auditor import audit_ec2_instances
from cost_auditor import get_month_to_date_cost
from notifier import send_audit_notification

# Configuración del logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Punto de entrada oficial (Handler) para AWS Lambda.
    Coordina la ejecución de la auditoría de EC2, consulta de costos y envío de notificaciones.
    Soporta modo simulación (Dry-Run / Chaos test) mediante {"simulate_alert": true}.

    :param event: Evento enviado por Amazon EventBridge o invocación manual.
    :param context: Contexto de ejecución de AWS Lambda.
    :return: Respuesta HTTP estandarizada.
    """
    logger.info("Iniciando auditoría diaria de AWS FinOps...")

    webhook_url = os.environ.get("WEBHOOK_URL")
    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
    required_tags_env = os.environ.get("REQUIRED_TAGS", "Owner,Environment")

    required_tags = [tag.strip() for tag in required_tags_env.split(",") if tag.strip()]

    # Verificación de modo simulación (Zero-Cost Dry-Run Test)
    if isinstance(event, dict) and event.get("simulate_alert") is True:
        logger.info("🧪 Modo Simulación Activado: Generando alerta de prueba sin costo...")
        ec2_uncompliant = [
            {
                "instance_id": "i-0a1b2c3d4e5f67890 (SIMULADO)",
                "instance_type": "t3.micro",
                "launch_time": "2026-08-18 14:30:00",
                "existing_tags": {"Owner": "DevTeam"},
                "missing_tags": ["Environment"]
            }
        ]
        cost_summary = {
            "status": "success",
            "total_cost_usd": 45.80,
            "start_date": "2026-08-01",
            "end_date": "2026-08-18"
        }
    else:
        # 1. Ejecutar auditoría real de EC2
        logger.info(f"Auditando etiquetas EC2 obligatorias: {required_tags}")
        ec2_uncompliant = audit_ec2_instances(required_tags=required_tags)

        # 2. Consultar costos acumulados del mes
        logger.info("Consultando gasto acumulado del mes en AWS Cost Explorer...")
        cost_summary = get_month_to_date_cost()

    # 3. Enviar notificación
    logger.info("Enviando informe de auditoría...")
    notification_sent = send_audit_notification(
        ec2_results=ec2_uncompliant,
        cost_results=cost_summary,
        webhook_url=webhook_url,
        sns_topic_arn=sns_topic_arn
    )

    summary = {
        "status": "success",
        "simulation": bool(isinstance(event, dict) and event.get("simulate_alert")),
        "ec2_uncompliant_count": len(ec2_uncompliant),
        "total_cost_usd": cost_summary.get("total_cost_usd", 0.0),
        "notification_sent": notification_sent
    }

    logger.info(f"Auditoría completada exitosamente: {json.dumps(summary)}")

    return {
        "statusCode": 200,
        "body": json.dumps(summary)
    }
