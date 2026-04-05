# IAM role for scheduler Lambda
resource "aws_iam_role" "config_evaluator" {
  name = "adb-config-evaluator-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "config_evaluator" {
  name = "adb-config-evaluator-policy"
  role = aws_iam_role.config_evaluator.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow"
        Action   = ["config:StartConfigRulesEvaluation"]
        Resource = "*"
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "config_evaluator" {
  filename         = "${path.module}/lambda/config_evaluator.zip"
  function_name    = "adb-config-evaluator-${var.environment}"
  role             = aws_iam_role.config_evaluator.arn
  handler          = "config_evaluator.handler"
  runtime          = "python3.12"
  timeout          = 30

  environment {
    variables = {
      ENVIRONMENT = var.environment
      #AWS_REGION  = var.aws_region
    }
  }

  source_code_hash = filebase64sha256(
    "${path.module}/lambda/config_evaluator.zip"
  )
}

# IAM role for EventBridge Scheduler
resource "aws_iam_role" "scheduler" {
  name = "adb-scheduler-role-${var.environment}"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "scheduler.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "scheduler" {
  name = "adb-scheduler-policy"
  role = aws_iam_role.scheduler.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = ["lambda:InvokeFunction"]
      Resource = aws_lambda_function.config_evaluator.arn
    }]
  })
}

# EventBridge Scheduler — runs every 1 hour
resource "aws_scheduler_schedule" "config_evaluator" {
  name       = "adb-config-evaluator-${var.environment}"
  group_name = "default"

  flexible_time_window {
    mode = "OFF"
  }

  # Every 1 hour
  schedule_expression = "rate(1 hour)"

  target {
    arn      = aws_lambda_function.config_evaluator.arn
    role_arn = aws_iam_role.scheduler.arn

    input = jsonencode({
      source    = "eventbridge-scheduler"
      detail    = "hourly-config-evaluation"
    })
  }
}

# Allow scheduler to invoke Lambda
resource "aws_lambda_permission" "scheduler" {
  statement_id  = "AllowScheduler"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.config_evaluator.function_name
  principal     = "scheduler.amazonaws.com"
  source_arn    = aws_scheduler_schedule.config_evaluator.arn
}