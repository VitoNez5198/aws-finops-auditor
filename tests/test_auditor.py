import json
import os
import sys
import boto3
from moto import mock_aws

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

from ec2_auditor import (
    audit_ec2_instances,
    audit_unattached_ebs_volumes,
    audit_unassociated_eips,
)
from cost_auditor import get_month_to_date_cost
from notifier import format_report_payload
from lambda_function import lambda_handler, resolve_webhook_url


@mock_aws
def test_ec2_auditor_detects_missing_tags():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    subnet = ec2_client.create_subnet(VpcId=vpc["Vpc"]["VpcId"], CidrBlock="10.0.1.0/24")

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
                {"Key": "Environment", "Value": "Dev"},
            ],
        }],
    )

    uncompliant_run = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        InstanceType="t2.micro",
        SubnetId=subnet["Subnet"]["SubnetId"],
        TagSpecifications=[{
            "ResourceType": "instance",
            "Tags": [{"Key": "Owner", "Value": "Victor"}],
        }],
    )
    uncompliant_id = uncompliant_run["Instances"][0]["InstanceId"]

    results = audit_ec2_instances(ec2_client=ec2_client, required_tags=("Owner", "Environment"))

    assert len(results) == 1
    assert results[0]["instance_id"] == uncompliant_id
    assert "Environment" in results[0]["missing_tags"]


@mock_aws
def test_ebs_auditor_detects_unattached_volumes():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    vol = ec2_client.create_volume(AvailabilityZone="us-east-1a", Size=20, VolumeType="gp3")

    results = audit_unattached_ebs_volumes(ec2_client=ec2_client)

    assert len(results) == 1
    assert results[0]["volume_id"] == vol["VolumeId"]
    assert results[0]["size_gb"] == 20


@mock_aws
def test_eip_auditor_detects_unassociated_addresses():
    ec2_client = boto3.client("ec2", region_name="us-east-1")
    eip = ec2_client.allocate_address(Domain="vpc")

    results = audit_unassociated_eips(ec2_client=ec2_client)

    assert len(results) == 1
    assert results[0]["allocation_id"] == eip["AllocationId"]


@mock_aws
def test_resolve_webhook_url_from_ssm(monkeypatch):
    ssm_client = boto3.client("ssm", region_name="us-east-1")
    ssm_client.put_parameter(
        Name="/finops-auditor/test/webhook-url",
        Value="https://discord.com/api/webhooks/123/abc",
        Type="SecureString",
    )
    monkeypatch.setenv("WEBHOOK_SSM_PARAM", "/finops-auditor/test/webhook-url")

    url = resolve_webhook_url(ssm_client=ssm_client)
    assert url == "https://discord.com/api/webhooks/123/abc"


def test_cost_auditor_fallback():
    cost_summary = get_month_to_date_cost()
    assert "total_cost_usd" in cost_summary
    assert isinstance(cost_summary["total_cost_usd"], float)


def test_notifier_payload_formatting_with_ebs_and_eip():
    ec2_results = [{"instance_id": "i-0123456789abcdef0", "instance_type": "t3.micro", "missing_tags": ["Environment"]}]
    ebs_results = [{"volume_id": "vol-12345", "size_gb": 30, "volume_type": "gp3"}]
    eip_results = [{"allocation_id": "eipalloc-123", "public_ip": "198.51.100.10"}]
    cost_results = {"total_cost_usd": 12.50, "start_date": "2026-11-01", "end_date": "2026-11-25"}

    payload = format_report_payload(ec2_results, cost_results, ebs_results=ebs_results, eip_results=eip_results)

    assert "i-0123456789abcdef0" in payload["content"]
    assert "vol-12345" in payload["content"]
    assert "198.51.100.10" in payload["content"]


def test_lambda_handler_simulation_mode():
    response = lambda_handler({"simulate_alert": True}, None)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["simulation"] is True
    assert body["ec2_uncompliant_count"] == 1
    assert body["unattached_ebs_count"] == 1
    assert body["unassociated_eip_count"] == 1
