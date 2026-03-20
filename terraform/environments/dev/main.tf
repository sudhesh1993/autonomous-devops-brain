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