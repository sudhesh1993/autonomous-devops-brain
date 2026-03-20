variable "environment" {
  type        = string
  description = "Environment name (dev or prod)"
}

variable "vpc_id" {
    type    =   string
    description = "VPC_ID"
}

variable "private_subnet_ids" {
    type = list(string)
    description = "private subnets of vpc"
}