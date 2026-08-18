import logging
import boto3

logger = logging.getLogger(__name__)


def audit_ec2_instances(ec2_client=None, required_tags=("Owner", "Environment")):
    """
    Inspecciona instancias EC2 en estado 'running' y detecta cuáles no poseen
    las etiquetas (tags) obligatorias especificadas.

    :param ec2_client: Cliente de boto3 para EC2 (opcional, para facilitar tests).
    :param required_tags: Iterable con las llaves de etiquetas obligatorias.
    :return: Lista de diccionarios con la información de las instancias no conformes.
    """
    if ec2_client is None:
        ec2_client = boto3.client("ec2")

    uncompliant_instances = []

    try:
        response = ec2_client.describe_instances(
            Filters=[
                {"Name": "instance-state-name", "Values": ["running"]}
            ]
        )

        for reservation in response.get("Reservations", []):
            for instance in reservation.get("Instances", []):
                instance_id = instance.get("InstanceId")
                instance_type = instance.get("InstanceType")
                launch_time = str(instance.get("LaunchTime"))

                # Convertir lista de tags [{'Key': '...', 'Value': '...'}] a un diccionario
                tags_list = instance.get("Tags", [])
                existing_tags = {tag["Key"]: tag["Value"] for tag in tags_list}

                # Verificar qué etiquetas faltan
                missing_tags = [
                    tag_key for tag_key in required_tags
                    if tag_key not in existing_tags
                ]

                if missing_tags:
                    uncompliant_instances.append({
                        "instance_id": instance_id,
                        "instance_type": instance_type,
                        "launch_time": launch_time,
                        "existing_tags": existing_tags,
                        "missing_tags": missing_tags
                    })

    except Exception as e:
        logger.error(f"Error al auditar instancias EC2: {str(e)}")
        raise e

    return uncompliant_instances
