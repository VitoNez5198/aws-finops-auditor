import json
import logging
import urllib.request
import boto3

logger = logging.getLogger(__name__)


def format_report_payload(ec2_results, cost_results):
    """
    Formatea los resultados de auditoría en un payload compatible con Webhooks de Discord/Slack.

    :param ec2_results: Lista de instancias EC2 sin etiquetas obligatorias.
    :param cost_results: Diccionario con la información de costos del mes.
    :return: Diccionario estructurado para la notificación.
    """
    total_cost = cost_results.get("total_cost_usd", 0.0)
    start_date = cost_results.get("start_date", "")
    end_date = cost_results.get("end_date", "")

    uncompliant_count = len(ec2_results)
    status_icon = "⚠️" if uncompliant_count > 0 else "✅"

    # Construcción de la lista de instancias para el mensaje
    instance_details = ""
    if uncompliant_count > 0:
        for inst in ec2_results:
            missing_str = ", ".join(inst.get("missing_tags", []))
            instance_details += f"• **`{inst.get('instance_id')}`** ({inst.get('instance_type')}) - Faltan tags: `{missing_str}`\n"
    else:
        instance_details = "✅ Todas las instancias EC2 activas cumplen con las etiquetas obligatorias.\n"

    # Formato compatible con Webhooks de Discord / Slack Embeds
    content = f"🛡️ **AWS FinOps & Resource Auditor - Reporte Diario**\n\n" \
              f"💰 **Gasto Acumulado del Mes**: `${total_cost} USD` *(Periodo: {start_date} al {end_date})*\n" \
              f"{status_icon} **Instancias EC2 No Conformes**: `{uncompliant_count}` detectadas\n\n" \
              f"{instance_details}"

    return {
        "content": content,
        "username": "AWS FinOps Auditor",
        "avatar_url": "https://aws.amazon.com/favicon.ico"
    }


def send_audit_notification(ec2_results, cost_results, webhook_url=None, sns_topic_arn=None, sns_client=None):
    """
    Envía el informe de auditoría a través de un Webhook HTTP o un Tema de Amazon SNS.

    :param ec2_results: Resultados de EC2.
    :param cost_results: Resultados de costos.
    :param webhook_url: URL del Webhook (Discord / Slack / Teams).
    :param sns_topic_arn: ARN del Tema de Amazon SNS (opcional).
    :param sns_client: Cliente boto3 SNS (opcional).
    :return: True si la notificación fue enviada correctamente.
    """
    payload = format_report_payload(ec2_results, cost_results)
    success = False

    # 1. Envío por Webhook HTTP (Discord / Slack)
    if webhook_url:
        try:
            req = urllib.request.Request(
                webhook_url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "User-Agent": "AWS-FinOps-Auditor-Lambda"
                },
                method="POST"
            )
            with urllib.request.urlopen(req) as response:
                if response.status in (200, 204):
                    logger.info("Notificación por Webhook enviada con éxito.")
                    success = True
                else:
                    logger.error(f"El Webhook respondió con código {response.status}")
        except Exception as e:
            logger.error(f"Error al enviar notificación por Webhook: {str(e)}")

    # 2. Envío por Amazon SNS (Opcional)
    if sns_topic_arn:
        if sns_client is None:
            sns_client = boto3.client("sns")

        try:
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Subject="🛡️ Reporte Diario AWS FinOps Auditor",
                Message=payload["content"]
            )
            logger.info("Notificación por Amazon SNS enviada con éxito.")
            success = True
        except Exception as e:
            logger.error(f"Error al enviar notificación por Amazon SNS: {str(e)}")

    if not webhook_url and not sns_topic_arn:
        logger.warning("No se proporcionó Webhook URL ni SNS Topic ARN. El reporte solo fue generado en logs.")
        logger.info(payload["content"])
        success = True

    return success
