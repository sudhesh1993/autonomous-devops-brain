## Status
Accepted

## Date
2026-03-22

## Context
During Week 2 development, the `INCOMING_SSH_DISABLED` Config
rule in `ap-south-2` did not fire automatically when a security
group was modified. Investigation revealed that this rule uses
**periodic evaluation** only — not change-triggered evaluation.

In newer AWS regions like `ap-south-2`, some managed Config rules
do not support change-triggered mode and default to periodic
evaluation (every 24 hours).

This means drift could go undetected for up to 24 hours in
production — unacceptable for an autonomous remediation platform.

## Decision
1. During development: call `start-config-rules-evaluation`
   manually after each infrastructure change to force immediate
   evaluation.

2. In production (Week 3): automate via EventBridge Scheduler
   to call `start-config-rules-evaluation` every 1 hour for
   all 5 Config rules.

## Consequences
- Drift detection delay reduced from 24 hours to max 1 hour
- Adds a small cost: ~$0.001 per rule evaluation per run
- 5 rules × 24 runs/day = ~$0.12/month — negligible
- Will be implemented as a Terraform EventBridge Scheduler
  resource in Week 3