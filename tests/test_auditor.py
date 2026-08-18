import os
import sys
import pytest
import boto3
from moto import mock_aws

# Agregar el directorio src al path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from ec2_auditor import audit_ec2_instances
from cost_auditor import get_month_to_date_cost
from notifier import format_report_payload, send_audit_notification


@mock_aws
def test_ec2_auditor_detects_missing_tags():
    """
    Prueba unitaria: Crea una instancia conforme (con Owner y Environment)
    y una instancia no conforme (sin Owner), verificando que el auditor detecte únicamente la no conforme.
    """
    ec2_client = boto3.client("ec2", region_name="us-east-1")

    # Crear una VPC y Subred requerida para lanzar la instancia en moto
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2_client.create_subnet(VpcId=vpc["Vpc"]["VpcId"], CidrBlock="10.0.1.0/24")

    # 1. Instancia Conforme (Tiene Owner y Environment)
    ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        SubnetId=subnet["Subnet"]["SubnetId"],
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Owner", "Value": "Victor"},
                {"Key": "Environment", "Value": "Dev"}
            ]
        }]
    )

    # 2. Instancia No Conforme (Solo tiene Owner, le falta Environment)
    uncompliant_run = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        SubnetId=subnet["Subnet"]["SubnetId"],
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [
                {"Key": "Owner", "Value": "Victor"}
            ]
        }]
    )
    uncompliant_id = uncompliant_run["Instances"][0]["InstanceId"]

    # Ejecutar el auditor
    results = audit_ec2_instances(ec2_client=ec2_client, required_tags=("Owner", "Environment"))

    # Assertions
    assert len(results) == 1
    assert results[0]["instance_id"] == uncompliant_id
    assert "Environment" in results[0]["missing_tags"]


def test_cost_auditor_fallback():
    """
    Prueba unitaria: Verifica que el auditor de costos retorne una estructura válida
    incluso si Cost Explorer no está disponible o falla.
    """
    cost_summary = get_month_to_date_cost()

    assert "total_cost_usd" in cost_summary
    assert "start_date" in cost_summary
    assert "end_date" in cost_summary
    assert isinstance(cost_summary["total_cost_usd"], float)


def test_notifier_payload_formatting():
    """
    Prueba unitaria: Verifica la construcción del mensaje de notificación.
    """
    ec2_results = [
        {
            "instance_id": "i-0123456789abcdef0",
            "instance_type": "t2.micro",
            "missing_tags": ["Environment"]
        }
    ]
    cost_results = {
        "total_cost_usd": 12.50,
        "start_date": "2026-08-01",
        "end_date": "2026-08-18"
    }

    payload = format_report_payload(ec2_results, cost_results)

    assert "content" in payload
    assert "$12.5 USD" in payload["content"] or "$12.50 USD" in payload["content"]
    assert "i-0123456789abcdef0" in payload["content"]
    assert "Environment" in payload["content"]


def test_lambda_handler_simulation_mode():
    """
    Prueba unitaria: Verifica que el modo simulación devuelva el payload de prueba sin invocar servicios reales.
    """
    from lambda_function import lambda_handler
    import json

    event = {"simulate_alert": True}
    response = lambda_handler(event, None)

    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["simulation"] is True
    assert body["ec2_uncompliant_count"] == 1

