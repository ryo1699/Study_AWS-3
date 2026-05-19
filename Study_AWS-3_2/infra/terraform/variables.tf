variable "aws_region" {
  type        = string
  description = "AWS region to deploy into."
  default     = "ap-northeast-1"
}

variable "project_name" {
  type        = string
  description = "Name prefix for AWS resources."
  default     = "study-aws-3-2"
}

variable "db_username" {
  type        = string
  description = "RDS application username."
  default     = "app_user"
}

variable "db_password" {
  type        = string
  description = "RDS application password."
  sensitive   = true
}

variable "allowed_ssh_cidr" {
  type        = string
  description = "CIDR allowed to SSH into the bastion."
  default     = "153.246.177.112/32"
}

variable "bastion_key_name" {
  type        = string
  description = "Existing EC2 key pair name used to SSH into the bastion."
  default     = "ryo-key"
}

variable "api_container_image" {
  type        = string
  description = "Initial API image URI. GitHub Actions updates this later."
  default     = "public.ecr.aws/docker/library/python:3.12-slim"
}

variable "frontend_container_image" {
  type        = string
  description = "Initial frontend image URI. GitHub Actions updates this later."
  default     = "public.ecr.aws/nginx/nginx:1.27-alpine"
}

variable "worker_container_image" {
  type        = string
  description = "Initial CSV worker image URI. GitHub Actions updates this later."
  default     = "public.ecr.aws/docker/library/python:3.12-slim"
}

variable "cloudfront_public_key_pem" {
  type        = string
  description = "Public key PEM used by CloudFront signed URLs."
}

variable "cloudfront_private_key_pem" {
  type        = string
  description = "Private key PEM used by the API to sign CloudFront URLs. Keep it out of Git."
  sensitive   = true
}

variable "maintenance_mode_enabled" {
  type        = bool
  description = "Attach a blocking WAF web ACL to CloudFront when true."
  default     = false
}
