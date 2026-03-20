module "eks" {
    source = "terraform-aws-modules/eks/aws"
    version = "20.8.4"

    cluster_name = "adb-cluster-${var.environment}"
    cluster_version = "1.29"
    vpc_id = var.vpc_id
    subnet_ids = var.private_subnet_ids
    cluster_endpoint_public_access = true

    enable_irsa = true

    eks_managed_node_groups = {
        core = {
            instance_type = ["t3.medium"]
            min_size = 1
            max_size = 3
            desired_size = 2

            labels = {
            role = "core"
            }
        }
    }
    cluster_additional_security_group_ids = []
    enable_cluster_creator_admin_permissions = true
}