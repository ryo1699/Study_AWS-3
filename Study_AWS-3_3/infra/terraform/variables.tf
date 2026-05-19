variable "aws_region" {
  type        = string
  description = "AWS region to deploy into."
  default     = "ap-northeast-1"
}

variable "project_name" {
  type        = string
  description = "Name prefix for AWS resources."
  default     = "study-aws-3-3"
}

variable "slack_webhook_url" {
  type        = string
  description = "Slack Incoming Webhook URL. Keep it out of Git."
  sensitive   = true
}

variable "batch_container_image" {
  type        = string
  description = "Initial ECS batch image URI. GitHub Actions updates this later."
  default     = "public.ecr.aws/docker/library/python:3.12-slim"
}

variable "eventbridge_schedule_expression" {
  type        = string
  description = "EventBridge schedule expression."
  default     = "rate(1 day)"
}

