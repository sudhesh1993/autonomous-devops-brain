# ADR 006 — Grafana dashboard import strategy

## Status
Accepted

## Date
2026-04-05

## Context
Dashboard needed to show unified view of:
- Kubernetes cluster health (nodes, pods, CPU, memory)
- Active alert counts by severity
- Alert activity trends over time
- CPU and memory trends per node

Two approaches considered:
1. Grafana provisioning via ConfigMap in Kubernetes
2. Dashboard JSON imported via Grafana HTTP API

## Decision
Import dashboard via Grafana API using curl.
Dashboard JSON stored in observability/grafana/ in GitHub.
Re-import after every terraform apply using the API call.

## Consequences
- Dashboard is version controlled in GitHub
- Re-import needed after each fresh terraform apply
- Auto-refresh set to 30 seconds for real-time visibility
- In Week 4 will add DynamoDB drift events panel
  using Grafana JSON datasource plugin
