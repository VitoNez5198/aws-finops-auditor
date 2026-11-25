import json
import logging
import urllib.request
import boto3

logger = logging.getLogger(__name__)


def format_report_payload(ec2_results, cost_results, ebs_results=None, eip_results=None):
    """Formatea los hallazgos FinOps en un payload para Webhook de Discord/Slack."""
    ebs_results = ebs_results or []
    eip_results = eip_results or []

    total_cost = cost_results.get("total_cost_usd", 0.0)
    start_date = cost_results.get("start_date", "")
    end_date = cost_results.get("end_date", "")

    uncompliant_count = len(ec2_results)
    ebs_count = len(ebs_results)
    eip_count = len(eip_results)

    ec2_status = "⚠️" if uncompliant_count > 0 else "✅"
    ebs_status = "⚠️" if ebs_count > 0 else "✅"
    eip_status = "⚠️" if eip_count > 0 else "✅"

    if uncompliant_count > 0:
        instance_details = "".join(
            f"• `{inst.get('instance_id')}` ({inst.get('instance_type')}) - Faltan tags: `{', '.join(inst.get('missing_tags', []))}`\n"
            for inst in ec2_results
        )
    else:
        instance_details = "• Todas las instancias EC2 activas cumplen con las etiquetas obligatorias.\n"

    if ebs_count > 0:
        total_gb = sum(v.get("size_gb", 0) for v in ebs_results)
        ebs_details = "".join(
            f"• `{v.get('volume_id')}` ({v.get('size_gb')} GB · {v.get('volume_type')})\n"
            for v in ebs_results
        )
        ebs_header = f"{ebs_status} **Volúmenes EBS Huérfanos**: `{ebs_count}` ({total_gb} GB sin uso)\n"
    else:
        ebs_details = "• Sin volúmenes EBS huérfanos.\n"
        ebs_header = f"{ebs_status} **Volúmenes EBS Huérfanos**: `0`\n"

    if eip_count > 0:
        eip_details = "".join(
            f"• `{eip.get('public_ip')}` (`{eip.get('allocation_id')}`)\n"
            for eip in eip_results
        )
    else:
        eip_details = "• Sin Elastic IPs sin asociar.\n"

    content = (
        f"🛡️ **AWS FinOps & Resource Auditor - Reporte Diario**\n\n"
        f"💰 **Gasto Acumulado del Mes**: `${total_cost} USD` *(Periodo: {start_date} al {end_date})*\n\n"
        f"{ec2_status} **Instancias EC2 No Conformes**: `{uncompliant_count}`\n"
        f"{instance_details}\n"
        f"{ebs_header}"
        f"{ebs_details}\n"
        f"{eip_status} **Elastic IPs Sin Asociar**: `{eip_count}`\n"
        f"{eip_details}"
    )

    return {
        "content": content,
        "username": "AWS FinOps Auditor",
        "avatar_url": "https://aws.amazon.com/favicon.ico",
    }


def send_audit_notification(
    ec2_results,
    cost_results,
    webhook_url=None,
    sns_topic_arn=None,
    sns_client=None,
    ebs_results=None,
    eip_results=None,
):
    """Envía el informe de auditoría por Webhook HTTP y/o Amazon SNS."""
    payload = format_report_payload(
        ec2_results,
        cost_results,
        ebs_results=ebs_results,
        eip_results=eip_results,
    )
    success = False

    if webhook_url and webhook_url.startswith("http"):
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "AWS-FinOps-Auditor-Lambda",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status in (200, 204):
                    logger.info("Notificación por Webhook enviada con éxito.")
                    success = True
                else:
                    logger.error(f"El Webhook respondió con código {response.status}")
        except Exception as e:
            logger.error(f"Error al enviar notificación por Webhook: {e}")

    if sns_topic_arn:
        if sns_client is None:
            sns_client = boto3.client("sns")
        try:
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject="Reporte Diario AWS FinOps Auditor",
                Message=payload["content"],
            )
            logger.info("Notificación por Amazon SNS enviada con éxito.")
            success = True
        except Exception as e:
            logger.error(f"Error al enviar notificación por Amazon SNS: {e}")

    if (not webhook_url or not webhook_url.startswith("http")) and not sns_topic_arn:
        logger.warning("Sin Webhook válido ni SNS Topic ARN. Reporte registrado solo en CloudWatch Logs.")
        logger.info(payload["content"])
        success = True

    return success
