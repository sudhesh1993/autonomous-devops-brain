import json
import boto3
import urllib3
import os
import uuid
from datetime import datetime, timezone

dynamodb = boto3.resource("dynamodb")
http     = urllib3.PoolManager()

TABLE_NAME        = os.environ["DYNAMODB_TABLE"]
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK", "")
ENVIRONMENT       = os.environ.get("ENVIRONMENT", "dev")

def find_existing_event(table, rule_name, resource_id):
    """Find the most recent DETECTED event for this rule+resource combo"""
    response = table.scan(
        FilterExpression="rule_name = :r AND resource_id = :ri AND #s = :s",
        ExpressionAttributeNames={"#s": "status"},
        ExpressionAttributeValues={
            ":r":  rule_name,
            ":ri": resource_id,
            ":s":  "DETECTED"
        }
    )
    items = response.get("Items", [])
    if not items:
        return None
    # Return the most recent one
    return sorted(items, key=lambda x: x["timestamp"], reverse=True)[0]


def handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    detail        = event.get("detail", {})
    rule_name     = detail.get("configRuleName", "unknown-rule")
    resource_id   = detail.get("resourceId", "unknown-resource")
    resource_type = detail.get("resourceType", "unknown-type")
    compliance    = detail.get("newEvaluationResult", {}).get("complianceType", "UNKNOWN")
    account_id    = event.get("account", "unknown")
    region        = event.get("region", "unknown")
    timestamp     = datetime.now(timezone.utc).isoformat()
    ttl_value     = int(datetime.now(timezone.utc).timestamp()) + (30 * 24 * 3600)

    table = dynamodb.Table(TABLE_NAME)

    if compliance == "NON_COMPLIANT":
        handle_drift_detected(
            table, rule_name, resource_id, resource_type,
            account_id, region, timestamp, ttl_value
        )

    elif compliance == "COMPLIANT":
        handle_drift_resolved(
            table, rule_name, resource_id, resource_type,
            account_id, region, timestamp
        )

    return {"statusCode": 200}


def handle_drift_detected(table, rule_name, resource_id, resource_type,
                           account_id, region, timestamp, ttl_value):
    event_id = str(uuid.uuid4())

    item = {
        "event_id":      event_id,
        "timestamp":     timestamp,
        "rule_name":     rule_name,
        "resource_id":   resource_id,
        "resource_type": resource_type,
        "compliance":    "NON_COMPLIANT",
        "account_id":    account_id,
        "region":        region,
        "environment":   ENVIRONMENT,
        "status":        "DETECTED",
        "ttl":           ttl_value
    }

    table.put_item(Item=item)
    print(f"Drift DETECTED logged: {event_id} | {rule_name} | {resource_id}")

    send_slack(
        color      = "danger",
        title      = ":rotating_light: Drift Detected",
        rule_name  = rule_name,
        resource_id= resource_id,
        resource_type = resource_type,
        status     = "DETECTED",
        event_id   = event_id,
        region     = region
    )


def handle_drift_resolved(table, rule_name, resource_id, resource_type,
                           account_id, region, timestamp):
    # Find the original DETECTED event and mark it RESOLVED
    existing = find_existing_event(table, rule_name, resource_id)

    if existing:
        # Update status to RESOLVED
        table.update_item(
            Key={
                "event_id":  existing["event_id"],
                "timestamp": existing["timestamp"]
            },
            UpdateExpression="SET #s = :s, resolved_at = :r",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={
                ":s": "RESOLVED",
                ":r": timestamp
            }
        )
        print(f"Drift RESOLVED: {existing['event_id']} | {rule_name} | {resource_id}")

        send_slack(
            color         = "good",
            title         = ":white_check_mark: Drift Resolved",
            rule_name     = rule_name,
            resource_id   = resource_id,
            resource_type = resource_type,
            status        = "RESOLVED",
            event_id      = existing["event_id"],
            region        = region
        )
    else:
        # No prior DETECTED record — log as a fresh COMPLIANT record anyway
        event_id = str(uuid.uuid4())
        table.put_item(Item={
            "event_id":      event_id,
            "timestamp":     timestamp,
            "rule_name":     rule_name,
            "resource_id":   resource_id,
            "resource_type": resource_type,
            "compliance":    "COMPLIANT",
            "account_id":    account_id,
            "region":        region,
            "environment":   ENVIRONMENT,
            "status":        "RESOLVED",
        })
        print(f"Compliant event logged (no prior DETECTED): {event_id}")

        send_slack(
            color         = "good",
            title         = ":white_check_mark: Drift Resolved",
            rule_name     = rule_name,
            resource_id   = resource_id,
            resource_type = resource_type,
            status        = "RESOLVED",
            event_id      = event_id,
            region        = region
        )


def send_slack(color, title, rule_name, resource_id,
               resource_type, status, event_id, region):
    if not SLACK_WEBHOOK_URL:
        return

    message = {
        "text": f"{title} | `{ENVIRONMENT}`",
        "attachments": [{
            "color":  color,
            "fields": [
                {"title": "Rule",          "value": rule_name,     "short": True},
                {"title": "Resource",      "value": resource_id,   "short": True},
                {"title": "Resource Type", "value": resource_type, "short": True},
                {"title": "Status",        "value": status,        "short": True},
                {"title": "Region",        "value": region,        "short": True},
                {"title": "Event ID",      "value": event_id,      "short": False},
            ],
            "footer": "Autonomous DevOps Brain"
        }]
    }

    http.request(
        "POST",
        SLACK_WEBHOOK_URL,
        body=json.dumps(message).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    print(f"Slack sent: {title}")