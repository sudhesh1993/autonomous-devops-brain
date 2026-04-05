# ADR 004 — AlertManager routing strategy

## Status
Accepted

## Date
2026-04-05

## Context
AlertmanagerConfig CRD was not being picked up because
alertmanagerConfigSelector was empty {} on the AlertManager
instance — meaning it ignores all CRDs entirely.

Two approaches were considered:
1. Helm values override using --reuse-values
2. Direct kubectl patch on the alertmanager secret

Helm upgrade failed due to nil pointer error on admission
webhook values between installed and chart versions.

Routing by team=adb label failed because AlertManager
was not seeing that label in its routing evaluation
despite Prometheus showing it correctly.

## Decision
1. Patch AlertManager config directly via kubectl secret patch
   bypassing Helm versioning issues entirely.
2. Route by alertname regex instead of team label —
   more explicit and reliable across AlertManager versions.

## Consequences
- AlertManager config changes must be made via kubectl patch
  not Helm values — document this for team
- Adding new alert rules requires updating the alertname
  regex in the route matcher
- Full DETECTED → RESOLVED lifecycle confirmed working
  for both Config drift and Kubernetes alerts