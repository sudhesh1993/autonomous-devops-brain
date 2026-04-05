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
  oidc_provider_arn = module.eks.oidc_provider_arn
  oidc_issuer       = replace(
    module.eks.oidc_provider_arn,
    "arn:aws:iam::${data.aws_caller_identity.current.account_id}:oidc-provider/",
    ""
  )
}

module "monitoring" {
  source           = "../../modules/monitoring"
  #grafana_password = var.grafana_password
  depends_on       = [module.eks]
}

module "scheduler" {
  source      = "../../modules/scheduler"
  environment = "dev"
  aws_region  = "ap-south-2"
  depends_on  = [module.config_rules]
}