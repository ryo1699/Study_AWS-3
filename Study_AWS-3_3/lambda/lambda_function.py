import json
import os
import urllib.request


def get_webhook_url() -> str:
    import boto3

    ssm = boto3.client("ssm")
    parameter_name = os.environ["SLACK_WEBHOOK_PARAMETER_NAME"]
    response = ssm.get_parameter(Name=parameter_name, WithDecryption=True)
    return response["Parameter"]["Value"]


def build_message(event: dict) -> dict:
    execution_name = event.get("executionName", "manual")
    batch_status = event.get("batchStatus", "UNKNOWN")
    return {
        "text": f"Study_AWS-3 課題3: ECS batch finished. execution={execution_name}, status={batch_status}"
    }


def lambda_handler(event, context):
    webhook_url = get_webhook_url()
    body = json.dumps(build_message(event)).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        response.read()
    return {"ok": True}
