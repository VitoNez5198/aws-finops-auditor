import logging
import boto3

logger = logging.getLogger(__name__)


def audit_ec2_instances(ec2_client=None, required_tags=("Owner", "Environment")):
    """Detecta instancias EC2 activas sin las etiquetas obligatorias."""
    if ec2_client is None:
        ec2_client = boto3.client("ec2")

    uncompliant_instances = []

    try:
        paginator = ec2_client.get_paginator("describe_instances")
        pages = paginator.paginate(
            Filters=[{"Name": "instance-state-name", "Values": ["running"]}]
        )

        for page in pages:
            for reservation in page.get("Reservations", []):
                for instance in reservation.get("Instances", []):
                    tags_list = instance.get("Tags", [])
                    existing_tags = {tag["Key"]: tag["Value"] for tag in tags_list}
                    missing_tags = [
                        tag_key for tag_key in required_tags
                        if tag_key not in existing_tags
                    ]

                    if missing_tags:
                        uncompliant_instances.append({
                            "instance_id": instance.get("InstanceId"),
                            "instance_type": instance.get("InstanceType"),
                            "launch_time": str(instance.get("LaunchTime")),
                            "existing_tags": existing_tags,
                            "missing_tags": missing_tags,
                        })
    except Exception as e:
        logger.error(f"Error al auditar instancias EC2: {e}")
        raise

    return uncompliant_instances


def audit_unattached_ebs_volumes(ec2_client=None):
    """Detecta volúmenes EBS huérfanos en estado 'available'."""
    if ec2_client is None:
        ec2_client = boto3.client("ec2")

    unattached_volumes = []

    try:
        paginator = ec2_client.get_paginator("describe_volumes")
        pages = paginator.paginate(
            Filters=[{"Name": "status", "Values": ["available"]}]
        )

        for page in pages:
            for volume in page.get("Volumes", []):
                unattached_volumes.append({
                    "volume_id": volume.get("VolumeId"),
                    "size_gb": volume.get("Size", 0),
                    "volume_type": volume.get("VolumeType", "unknown"),
                    "availability_zone": volume.get("AvailabilityZone", ""),
                })
    except Exception as e:
        logger.error(f"Error al auditar volúmenes EBS: {e}")
        raise

    return unattached_volumes


def audit_unassociated_eips(ec2_client=None):
    """Detecta Elastic IPs asignadas a la cuenta pero sin asociar a ningún recurso."""
    if ec2_client is None:
        ec2_client = boto3.client("ec2")

    unassociated_eips = []

    try:
        response = ec2_client.describe_addresses()
        for address in response.get("Addresses", []):
            if not address.get("AssociationId"):
                unassociated_eips.append({
                    "allocation_id": address.get("AllocationId"),
                    "public_ip": address.get("PublicIp"),
                })
    except Exception as e:
        logger.error(f"Error al auditar Elastic IPs: {e}")
        raise

    return unassociated_eips
