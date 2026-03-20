module "vpc" {
  source      = "../../modules/vpc"
  environment = "dev"
}