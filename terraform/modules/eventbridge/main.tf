# DynamoDB table to store every drift event
resource "aws_dynamodb_table" "drift_log" {
  name         = "adb-drift-log-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "event_id"
  range_key    = "timestamp"

  attribute {
    name = "event_id"
    type = "S"
  }
  attribute {
    name = "timestamp"
    type = "S"
  }
  attribute {
    name = "rule_name"    # ← add this
    type = "S"
  }

  # GSI so we can query by rule_name efficiently
  global_secondary_index {
    name            = "rule_name-index"
    hash_key        = "rule_name"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
}

# IAM role for Lambda
resource "aws_iam_role" "drift_processor" {
  name = "adb-drift-processor-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "drift_processor" {
  name = "adb-drift-processor-policy"
  role = aws_iam_role.drift_processor.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["dynamodb:PutItem", "dynamodb:GetItem", "dynamodb:Query", "dynamodb:Scan", "dynamodb:UpdateItem"]
        Resource = aws_dynamodb_table.drift_log.arn
      }
    ]
  })
}

# Lambda function — drift event processor
resource "aws_lambda_function" "drift_processor" {
  filename         = "${path.module}/lambda/drift_processor.zip"
  function_name    = "adb-drift-processor-${var.environment}"
  role             = aws_iam_role.drift_processor.arn
  handler          = "drift_processor.handler"
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      DYNAMODB_TABLE = aws_dynamodb_table.drift_log.name
      ENVIRONMENT    = var.environment
      SLACK_WEBHOOK  = var.slack_webhook_url
    }
  }

  source_code_hash = filebase64sha256("${path.module}/lambda/drift_processor.zip")
}

# EventBridge rule — catch all AWS Config compliance changes
resource "aws_cloudwatch_event_rule" "config_drift" {
  name        = "adb-config-drift-${var.environment}"
  description = "Captures AWS Config compliance and Prometheus alert events"

  event_pattern = jsonencode({
    source      = ["aws.config", "myapp.testing", "custom.prometheus"]
    detail-type = ["Config Rules Compliance Change", "Prometheus Alert"]
  })
}

# Wire EventBridge to Lambda
resource "aws_cloudwatch_event_target" "drift_to_lambda" {
  rule      = aws_cloudwatch_event_rule.config_drift.name
  target_id = "drift-processor"
  arn       = aws_lambda_function.drift_processor.arn
}

# Allow EventBridge to invoke Lambda
resource "aws_lambda_permission" "eventbridge" {
  statement_id  = "AllowEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.drift_processor.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.config_drift.arn
}

# IAM role for alert receiver pod (uses IRSA)
resource "aws_iam_role" "alert_receiver" {
  name = "adb-alert-receiver-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = var.oidc_provider_arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "${var.oidc_issuer}:sub" = "system:serviceaccount:monitoring:adb-alert-receiver"
          "${var.oidc_issuer}:aud" = "sts.amazonaws.com"
        }
      }
    }]
  })
}

resource "aws_iam_role_policy" "alert_receiver" {
  name = "adb-alert-receiver-policy"
  role = aws_iam_role.alert_receiver.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["events:PutEvents"]
      Resource = "*"
    }]
  })
}