# Autonomous DevOps Brain

> AI-powered platform that autonomously detects infrastructure drift
> and remediates incidents on AWS — without human intervention.

![Status](https://img.shields.io/badge/status-building%20in%20public-orange)
![AWS](https://img.shields.io/badge/AWS-EKS%20%7C%20Bedrock%20%7C%20Config-yellow)
![IaC](https://img.shields.io/badge/IaC-Terraform-purple)

## What it does

1. **Detects** — Prometheus alerts + AWS Config drift events flow into EventBridge
2. **Diagnoses** — LangChain agent on AWS Bedrock performs root cause analysis
3. **Decides** — Confidence-scored decision engine picks the right runbook
4. **Fixes** — Auto-applies fix (K8s action / Terraform PR / SSM runbook)
5. **Audits** — Every action logged to DynamoDB + S3, reported to Slack

## Stack

- **Cloud:** AWS (EKS, Bedrock, Config, EventBridge, Lambda, SSM, DynamoDB)
- **IaC:** Terraform (modular, remote state, multi-env)
- **AI:** AWS Bedrock (Claude) + LangChain agents
- **Observability:** Prometheus + Grafana + CloudWatch
- **GitOps:** GitHub Actions + ArgoCD

## 🚧 Building in public — follow the journey

- [ ] Month 1: Foundation + Drift detection
- [ ] Month 2: AI Brain (RCA + Decision engine)
- [ ] Month 3: Action layer (self-healing)
- [ ] Month 4: Audit trail + Demo

## Blogs

---
Created by Sudhesh · Senior DevOps Engineer