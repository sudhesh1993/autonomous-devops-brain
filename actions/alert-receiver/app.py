import json
import boto3
import os
import logging
from flask import Flask, request, jsonify

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

events_client = boto3.client(
    "events",
    region_name=os.environ.get("AWS_REGION", "ap-south-2")
)

EVENT_BUS_NAME = os.environ.get("EVENT_BUS_NAME", "default")


def build_event_detail(alert):
    """Convert Prometheus alert to our standard event format"""
    labels      = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    status      = alert.get("status", "firing")

    return {
        "alertName":   labels.get("alertname", "unknown"),
        "severity":    labels.get("severity", "warning"),
        "status":      status,                    # firing or resolved
        "namespace":   labels.get("namespace", "unknown"),
        "pod":         labels.get("pod", ""),
        "node":        labels.get("node", ""),
        "deployment":  labels.get("deployment", ""),
        "summary":     annotations.get("summary", ""),
        "description": annotations.get("description", ""),
        "source":      "prometheus",
        "rawLabels":   json.dumps(labels)
    }


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy"}), 200


@app.route("/alert", methods=["POST"])
def receive_alert():
    payload = request.get_json(force=True)
    logger.info(f"Received AlertManager payload: {json.dumps(payload)}")

    alerts = payload.get("alerts", [])
    if not alerts:
        return jsonify({"message": "no alerts"}), 200

    entries = []
    for alert in alerts:
        detail = build_event_detail(alert)
        logger.info(f"Processing alert: {detail['alertName']} status={detail['status']}")

        entries.append({
            "Source":     "custom.prometheus",
            "DetailType": "Prometheus Alert",
            "Detail":     json.dumps(detail),
            "EventBusName": EVENT_BUS_NAME
        })

    # Send all alerts to EventBridge in one call
    if entries:
        response = events_client.put_events(Entries=entries)
        failed   = response.get("FailedEntryCount", 0)
        if failed > 0:
            logger.error(f"Failed to send {failed} events to EventBridge")
        else:
            logger.info(f"Sent {len(entries)} events to EventBridge")

    return jsonify({"received": len(entries)}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)