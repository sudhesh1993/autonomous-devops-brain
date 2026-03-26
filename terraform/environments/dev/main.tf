data "aws_caller_identity" "current" {}

module "vpc" {
  source      = "../../modules/vpc"
  environment = "dev"
}

module "eks" {
  source             = "../../modules/eks"
  environment        = "dev"
  vpc_id             = module.vpc.vpc_id
  private_subnet_ids = module.vpc.private_subnet_ids
}

module "config_rules" {
  source      = "../../modules/config-rules"
  environment = "dev"
  account_id  = data.aws_caller_identity.current.account_id
}

module "eventbridge" {
  source            = "../../modules/eventbridge"
  environment       = "dev"
  slack_webhook_url = var.slack_webhook_url
}