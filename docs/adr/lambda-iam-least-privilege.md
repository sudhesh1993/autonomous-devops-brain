# ADR 002 — Lambda IAM permissions for DynamoDB operations

## Status
Accepted

## Date
2026-03-22

## Context
During Week 2 development, the Lambda drift processor threw an
`AccessDeniedException` when handling COMPLIANT events:

    User: arn:aws:sts::<awsaccountid>:assumed-role/adb-drift-processor-dev
    is not authorized to perform: dynamodb:Scan

Root cause: the initial IAM policy only granted `PutItem`,
`GetItem`, and `Query`. The RESOLVED flow requires:

- `dynamodb:Scan` — to find the existing DETECTED record
  for the same rule + resource combination
- `dynamodb:UpdateItem` — to flip status from DETECTED to RESOLVED

This was caught via CloudWatch Logs trace — the error showed
the exact missing permission and the exact ARN attempting the call.

## Decision
Add `dynamodb:Scan` and `dynamodb:UpdateItem` to the Lambda
IAM policy. Both permissions are scoped to the specific
`adb-drift-log-dev` table ARN only — no wildcard resources.

## Consequences
- Lambda can now complete the full DETECTED → RESOLVED lifecycle
- Permissions remain least-privilege — table-scoped, not account-wide
- Debugged via CloudWatch Logs — confirms observability setup works
- In future: replace Scan with a GSI Query for better performance
  as the drift log table grows beyond 10,000 records