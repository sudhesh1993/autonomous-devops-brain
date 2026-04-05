# ADR 005 — Config rules evaluation strategy

## Status
Accepted

## Date
2026-04-05

## Context
Initial implementation evaluated each Config rule sequentially
with delays between calls. This caused:
- Lambda timeouts (120s not enough for 5 rules + delays)
- LimitExceededException from heavy manual testing
- Unpredictable execution time

## Decision
Evaluate all 5 Config rules in a single
StartConfigRulesEvaluation API call passing the full list.
AWS Config supports multiple rule names in one call.
Lambda timeout reduced to 30 seconds.

## Consequences
- Execution time reduced from ~120s to under 2 seconds
- Single API call = single rate limit token consumed
- In production (hourly schedule) rate limit never hit
- LimitExceededException only occurs during heavy
  manual testing — not a production concern
