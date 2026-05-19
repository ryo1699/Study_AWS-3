output "cloudfront_domain_name" {
  value = aws_cloudfront_distribution.app.domain_name
}

output "alb_dns_name" {
  value = aws_lb.app.dns_name
}

output "api_ecr_repository_name" {
  value = aws_ecr_repository.api.name
}

output "frontend_ecr_repository_name" {
  value = aws_ecr_repository.frontend.name
}

output "worker_ecr_repository_name" {
  value = aws_ecr_repository.worker.name
}

output "api_ecr_repository_url" {
  value = aws_ecr_repository.api.repository_url
}

output "frontend_ecr_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "worker_ecr_repository_url" {
  value = aws_ecr_repository.worker.repository_url
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "api_ecs_service_name" {
  value = aws_ecs_service.api.name
}

output "frontend_ecs_service_name" {
  value = aws_ecs_service.frontend.name
}

output "worker_ecs_service_name" {
  value = aws_ecs_service.worker.name
}

output "api_task_definition_family" {
  value = aws_ecs_task_definition.api.family
}

output "frontend_task_definition_family" {
  value = aws_ecs_task_definition.frontend.family
}

output "worker_task_definition_family" {
  value = aws_ecs_task_definition.worker.family
}

output "rds_endpoint" {
  value = aws_db_instance.postgres.address
}

output "bastion_public_ip" {
  value = aws_instance.bastion.public_ip
}

output "image_bucket_name" {
  value = aws_s3_bucket.images.bucket
}

output "csv_bucket_name" {
  value = aws_s3_bucket.csv_exports.bucket
}

output "csv_export_queue_url" {
  value = aws_sqs_queue.csv_export.url
}
