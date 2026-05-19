output "batch_ecr_repository_name" {
  value = aws_ecr_repository.batch.name
}

output "batch_ecr_repository_url" {
  value = aws_ecr_repository.batch.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "batch_task_definition_family" {
  value = aws_ecs_task_definition.batch.family
}

output "step_functions_state_machine_arn" {
  value = aws_sfn_state_machine.batch_then_slack.arn
}

output "eventbridge_rule_name" {
  value = aws_cloudwatch_event_rule.schedule.name
}

output "slack_webhook_parameter_name" {
  value = aws_ssm_parameter.slack_webhook_url.name
}

