# IAM role for AWS Config to use
resource "aws_iam_role" "config" {
  name = "adb-config-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "config.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "config" {
  role       = aws_iam_role.config.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWS_ConfigRole"
}

# S3 bucket for Config delivery
resource "aws_s3_bucket" "config" {
  bucket        = "adb-config-delivery-${var.environment}-${var.account_id}"
  force_destroy = true
}

resource "aws_s3_bucket_policy" "config" {
  bucket = aws_s3_bucket.config.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "AWSConfigBucketPermissionsCheck"
        Effect = "Allow"
        Principal = { Service = "config.amazonaws.com" }
        Action   = "s3:GetBucketAcl"
        Resource = "arn:aws:s3:::${aws_s3_bucket.config.bucket}"
      },
      {
        Sid    = "AWSConfigBucketDelivery"
        Effect = "Allow"
        Principal = { Service = "config.amazonaws.com" }
        Action   = "s3:PutObject"
        Resource = "arn:aws:s3:::${aws_s3_bucket.config.bucket}/AWSLogs/*"
        Condition = {
          StringEquals = { "s3:x-amz-acl" = "bucket-owner-full-control" }
        }
      }
    ]
  })
}

# Config recorder
resource "aws_config_configuration_recorder" "main" {
  name     = "adb-config-recorder-${var.environment}"
  role_arn = aws_iam_role.config.arn

  recording_group {
    all_supported                 = true
    include_global_resource_types = true
  }
}

# Config delivery channel
resource "aws_config_delivery_channel" "main" {
  name           = "adb-config-delivery-${var.environment}"
  s3_bucket_name = aws_s3_bucket.config.bucket
  depends_on     = [aws_config_configuration_recorder.main]
}

# Start recording
resource "aws_config_configuration_recorder_status" "main" {
  name       = aws_config_configuration_recorder.main.name
  is_enabled = true
  depends_on = [aws_config_delivery_channel.main]
}

# Rule 1 — no unrestricted SSH (port 22 open to 0.0.0.0/0)
resource "aws_config_config_rule" "no_unrestricted_ssh" {
  name = "adb-no-unrestricted-ssh"
  source {
    owner             = "AWS"
    source_identifier = "INCOMING_SSH_DISABLED"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

# Rule 2 — S3 buckets must not be public
resource "aws_config_config_rule" "s3_no_public_access" {
  name = "adb-s3-no-public-access"
  source {
    owner             = "AWS"
    source_identifier = "S3_BUCKET_PUBLIC_READ_PROHIBITED"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

# Rule 3 — root account must not have active access keys
resource "aws_config_config_rule" "no_root_access_key" {
  name = "adb-no-root-access-key"
  source {
    owner             = "AWS"
    source_identifier = "IAM_ROOT_ACCESS_KEY_CHECK"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

# Rule 4 — EBS volumes must be encrypted
resource "aws_config_config_rule" "ebs_encrypted" {
  name = "adb-ebs-encrypted"
  source {
    owner             = "AWS"
    source_identifier = "ENCRYPTED_VOLUMES"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}

# Rule 5 — CloudTrail must be enabled (replaces MFA rule, fully supported in ap-south-2)
resource "aws_config_config_rule" "cloudtrail_enabled" {
  name = "adb-cloudtrail-enabled"
  source {
    owner             = "AWS"
    source_identifier = "CLOUD_TRAIL_ENABLED"
  }
  depends_on = [aws_config_configuration_recorder_status.main]
}