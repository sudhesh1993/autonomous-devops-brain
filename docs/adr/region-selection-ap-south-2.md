# ADR 003 — AWS region selection

## Status
Accepted

## Date
2026-03-22

## Context
Project is being developed from Hyderabad, India. Two candidate
regions were considered:

- `ap-south-1` — Mumbai (older, more services available)
- `ap-south-2` — Hyderabad (newer, closer proximity)

Key finding: AWS Bedrock (required for Month 2 AI brain) is
not yet available in `ap-south-2`.

## Decision
Use `ap-south-2` (Hyderabad) as the primary region for all
infrastructure: EKS, Config, EventBridge, Lambda, DynamoDB, S3.

For AWS Bedrock (Month 2 onwards): use `us-east-1` via
cross-region API call from Lambda. Latency impact is acceptable
since incident remediation is async — not real-time user-facing.

## Consequences
- Lower network latency from development machine to AWS
- Some newer managed Config rules not available in ap-south-2
  (handled in ADR 001)
- Bedrock cross-region adds ~100-150ms per LLM call — acceptable
- Cross-region Bedrock calls may incur minor data transfer cost