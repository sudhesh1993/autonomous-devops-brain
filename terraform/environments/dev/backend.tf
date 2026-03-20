terraform {
  backend "s3" {
    bucket         = "adb-terraform-state-devenv"
    key            = "adb/dev/terraform.tfstate"
    region         = "ap-south-2"
    dynamodb_table = "adb-terraform-locks"
    encrypt        = true
  }
}