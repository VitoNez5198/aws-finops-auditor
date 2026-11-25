import json
import logging
import os
import boto3
from ec2_auditor import (
    audit_ec2_instances,
    audit_unattached_ebs_volumes,
    audit_unassociated_eips,
)
from cost_auditor import get_month_to_date_cost
from notifier import send_audit_notification

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def resolve_webhook_url(ssm_client=None):
    """Obtiene la URL del webhook desde SSM Parameter Store (SecureString) o variable de entorno."""
    ssm_param = os.environ.get("WEBHOOK_SSM_PARAM")
    if ssm_param:
        try:
            if ssm_client is None:
                ssm_client = boto3.client("ssm")
            response = ssm_client.get_parameter(Name=ssm_param, WithDecryption=True)
            value = response["Parameter"]["Value"].strip()
            if value.startswith("http"):
                return value
            return None
        except Exception as e:
            logger.error(f"No se pudo leer el parámetro SSM {ssm_param}: {e}")

    env_url = os.environ.get("WEBHOOK_URL", "").strip()
    return env_url if env_url.startswith("http") else None


def lambda_handler(event, context):
    """Handler de AWS Lambda: audita EC2, EBS huérfanos, Elastic IPs y costo mensual."""
    logger.info("Iniciando auditoría diaria de AWS FinOps...")

    webhook_url = resolve_webhook_url()
    sns_topic_arn = os.environ.get("SNS_TOPIC_ARN")
    required_tags_env = os.environ.get("REQUIRED_TAGS", "Owner,Environment")
    required_tags = [tag.strip() for tag in required_tags_env.split(",") if tag.strip()]

    is_simulation = isinstance(event, dict) and event.get("simulate_alert") is True

    if is_simulation:
        logger.info("Modo simulación activado: generando reporte de prueba sin costo.")
        ec2_uncompliant = [
            {
                "instance_id": "i-0a1b2c3d4e5f67890 (SIMULADO)",
                "instance_type": "t3.micro",
                "launch_time": "2026-11-25 12:00:00",
                "existing_tags": {"Owner": "DevTeam"},
                "missing_tags": ["Environment"],
            }
        ]
        unattached_ebs = [
            {
                "volume_id": "vol-0abc123456789def0 (SIMULADO)",
                "size_gb": 30,
                "volume_type": "gp3",
                "availability_zone": "us-east-1a",
            }
        ]
        unassociated_eips = [
            {
                "allocation_id": "eipalloc-0123456789abcdef0",
                "public_ip": "198.51.100.42 (SIMULADO)",
            }
        ]
        cost_summary = {
            "status": "success",
            "total_cost_usd": 45.80,
            "start_date": "2026-11-01",
            "end_date": "2026-11-25",
        }
    else:
        logger.info(f"Auditando etiquetas EC2 obligatorias: {required_tags}")
        ec2_uncompliant = audit_ec2_instances(required_tags=required_tags)
        unattached_ebs = audit_unattached_ebs_volumes()
        unassociated_eips = audit_unassociated_eips()
        cost_summary = get_month_to_date_cost()

    notification_sent = send_audit_notification(
        ec2_results=ec2_uncompliant,
        cost_results=cost_summary,
        webhook_url=webhook_url,
        sns_topic_arn=sns_topic_arn,
        ebs_results=unattached_ebs,
        eip_results=unassociated_eips,
    )

    summary = {
        "status": "success",
        "simulation": is_simulation,
        "ec2_uncompliant_count": len(ec2_uncompliant),
        "unattached_ebs_count": len(unattached_ebs),
        "unassociated_eip_count": len(unassociated_eips),
        "total_cost_usd": cost_summary.get("total_cost_usd", 0.0),
        "notification_sent": notification_sent,
    }

    logger.info(f"Auditoría completada: {json.dumps(summary)}")

    return {
        "statusCode": 200,
        "body": json.dumps(summary),
    }
