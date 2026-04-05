output "evaluator_function_name" {
  value = aws_lambda_function.config_evaluator.function_name
}

output "schedule_name" {
  value = aws_scheduler_schedule.config_evaluator.name
}