import json
import boto3
import urllib3
import os
import uuid
from datetime import datetime, timezone
from boto3.dynamodb.conditions import Attr

dynamodb = boto3.resource("dynamodb")
http     = urllib3.PoolManager()

TABLE_NAME        = os.environ["DYNAMODB_TABLE"]
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK", "")
ENVIRONMENT       = os.environ.get("ENVIRONMENT", "dev")


# ─────────────────────────────────────────
# Main handler
# ─────────────────────────────────────────

def handler(event, context):
    print(f"Received event: {json.dumps(event)}")

    source      = event.get("source", "")
    detail_type = event.get("detail-type", "")

    print(f"Source: {source} | DetailType: {detail_type}")

    if source in ["aws.config", "myapp.testing"]:
        handle_config_event(event)

    elif source == "custom.prometheus":
        handle_prometheus_event(event)

    else:
        print(f"Unknown source: {source} — skipping")

    return {"statusCode": 200}


# ─────────────────────────────────────────
# Config event handlers
# ─────────────────────────────────────────

def handle_config_event(event):
    detail        = event.get("detail", {})
    rule_name     = detail.get("configRuleName", "unknown-rule")
    resource_id   = detail.get("resourceId", "unknown-resource")
    resource_type = detail.get("resourceType", "unknown-type")
    compliance    = detail.get("newEvaluationResult", {}).get("complianceType", "UNKNOWN")
    account_id    = event.get("account", "unknown")
    region        = event.get("region", "unknown")
    timestamp     = datetime.now(timezone.utc).isoformat()
    ttl_value     = int(datetime.now(timezone.utc).timestamp()) + (30 * 24 * 3600)

    print(f"Config event: {compliance} | {rule_name} | {resource_id}")

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
    else:
        print(f"Unknown compliance type: {compliance} — skipping")


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
        "source":        "aws.config",
        "ttl":           ttl_value
    }

    table.put_item(Item=item)
    print(f"Drift DETECTED logged: {event_id} | {rule_name} | {resource_id}")

    send_slack(
        color         = "danger",
        title         = ":rotating_light: Drift Detected",
        rule_name     = rule_name,
        resource_id   = resource_id,
        resource_type = resource_type,
        status        = "DETECTED",
        event_id      = event_id,
        region        = region
    )


def handle_drift_resolved(table, rule_name, resource_id, resource_type,
                           account_id, region, timestamp):
    existing = find_existing_event(table, rule_name, resource_id)

    if existing:
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
        # No prior DETECTED record — log fresh RESOLVED anyway
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
            "source":        "aws.config",
        })
        print(f"Fresh RESOLVED logged (no prior DETECTED): {event_id}")

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


# ─────────────────────────────────────────
# Prometheus event handlers
# ─────────────────────────────────────────

def handle_prometheus_event(event):
    detail     = event.get("detail", {})
    alert_name = detail.get("alertName", "unknown")
    status     = detail.get("status", "firing")
    severity   = detail.get("severity", "warning")
    namespace  = detail.get("namespace", "unknown")
    pod        = detail.get("pod", "")
    node       = detail.get("node", "")
    summary    = detail.get("summary", "")
    timestamp  = datetime.now(timezone.utc).isoformat()
    ttl_value  = int(datetime.now(timezone.utc).timestamp()) + (30 * 24 * 3600)

    # Pick best resource identifier
    resource_id = pod or node or namespace

    print(f"Prometheus event: {alert_name} | status={status} | resource={resource_id}")

    table = dynamodb.Table(TABLE_NAME)

    if status == "firing":
        handle_k8s_alert_firing(
            table, alert_name, resource_id, severity,
            summary, namespace, timestamp, ttl_value
        )
    elif status == "resolved":
        handle_k8s_alert_resolved(
            table, alert_name, resource_id,
            summary, timestamp
        )
    else:
        print(f"Unknown Prometheus status: {status} — skipping")


def handle_k8s_alert_firing(table, alert_name, resource_id, severity,
                              summary, namespace, timestamp, ttl_value):
    event_id = str(uuid.uuid4())

    item = {
        "event_id":      event_id,
        "timestamp":     timestamp,
        "rule_name":     alert_name,
        "resource_id":   resource_id,
        "resource_type": "Kubernetes",
        "compliance":    "FIRING",
        "account_id":    "eks",
        "region":        "ap-south-2",
        "environment":   ENVIRONMENT,
        "status":        "DETECTED",
        "severity":      severity,
        "summary":       summary,
        "namespace":     namespace,
        "source":        "prometheus",
        "ttl":           ttl_value
    }

    table.put_item(Item=item)
    print(f"K8s alert FIRING logged: {event_id} | {alert_name} | {resource_id}")

    send_slack(
        color         = "danger",
        title         = ":rotating_light: K8s Alert Firing",
        rule_name     = alert_name,
        resource_id   = resource_id,
        resource_type = f"Kubernetes | {severity.upper()}",
        status        = "FIRING",
        event_id      = event_id,
        region        = "ap-south-2"
    )


def handle_k8s_alert_resolved(table, alert_name, resource_id,
                                summary, timestamp):
    existing = find_existing_event(table, alert_name, resource_id)

    if existing:
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
        print(f"K8s alert RESOLVED: {existing['event_id']} | {alert_name} | {resource_id}")

        send_slack(
            color         = "good",
            title         = ":white_check_mark: K8s Alert Resolved",
            rule_name     = alert_name,
            resource_id   = resource_id,
            resource_type = "Kubernetes",
            status        = "RESOLVED",
            event_id      = existing["event_id"],
            region        = "ap-south-2"
        )
    else:
        print(f"No DETECTED record found for {alert_name} / {resource_id} — logging fresh RESOLVED")
        event_id = str(uuid.uuid4())
        table.put_item(Item={
            "event_id":      event_id,
            "timestamp":     timestamp,
            "rule_name":     alert_name,
            "resource_id":   resource_id,
            "resource_type": "Kubernetes",
            "compliance":    "RESOLVED",
            "account_id":    "eks",
            "region":        "ap-south-2",
            "environment":   ENVIRONMENT,
            "status":        "RESOLVED",
            "source":        "prometheus",
        })

        send_slack(
            color         = "good",
            title         = ":white_check_mark: K8s Alert Resolved",
            rule_name     = alert_name,
            resource_id   = resource_id,
            resource_type = "Kubernetes",
            status        = "RESOLVED",
            event_id      = event_id,
            region        = "ap-south-2"
        )


# ─────────────────────────────────────────
# Shared utilities
# ─────────────────────────────────────────

def find_existing_event(table, rule_name, resource_id):
    """Find most recent DETECTED event for rule + resource combo"""
    response = table.scan(
        FilterExpression=(
            Attr("rule_name").eq(rule_name) &
            Attr("resource_id").eq(resource_id) &
            Attr("status").eq("DETECTED")
        )
    )
    items = response.get("Items", [])
    if not items:
        print(f"No DETECTED record found for {rule_name} / {resource_id}")
        return None
    return sorted(items, key=lambda x: x["timestamp"], reverse=True)[0]


def send_slack(color, title, rule_name, resource_id,
               resource_type, status, event_id, region):
    if not SLACK_WEBHOOK_URL:
        print("No Slack webhook configured — skipping")
        return

    message = {
        "text": f"{title} | `{ENVIRONMENT}`",
        "attachments": [{
            "color":  color,
            "fields": [
                {"title": "Rule / Alert",  "value": rule_name,     "short": True},
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
    print(f"Slack notification sent: {title}")