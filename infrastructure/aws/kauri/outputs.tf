output "ec2_public_ip" {
  description = "Elastic IP assigned to the Kauri host."
  value       = aws_eip.kauri.public_ip
}

output "ec2_instance_id" {
  description = "Instance ID of the Kauri host."
  value       = aws_instance.kauri.id
}

output "knowledge_bucket" {
  description = "S3 bucket storing the base connaissances and dumps."
  value       = aws_s3_bucket.base_connaissances.bucket
}

output "ssh_command" {
  description = "Helper SSH command."
  value       = "ssh -i <path-to-private-key> ubuntu@${aws_eip.kauri.public_ip}"
}

output "ssm_parameter_prefix" {
  description = "Prefix used for Kauri secrets in Parameter Store."
  value       = "/${var.project_name}/"
}
