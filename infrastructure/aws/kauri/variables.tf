variable "aws_region" {
  description = "AWS region to deploy Kauri demo infrastructure."
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Project tag used across all resources."
  type        = string
  default     = "kauri"
}

variable "environment" {
  description = "Environment tag (e.g., demo, staging, prod)."
  type        = string
  default     = "demo"
}

variable "additional_tags" {
  description = "Optional extra tags applied to every resource."
  type        = map(string)
  default     = {}
}

variable "ssh_key_name" {
  description = "Existing AWS EC2 key pair name used for the instance."
  type        = string
}

variable "allowed_ssh_cidr" {
  description = "CIDR range allowed to reach SSH and Grafana."
  type        = string
  default     = "0.0.0.0/0"
}

variable "ec2_instance_type" {
  description = "Instance type hosting the Docker stack (ARM recommended for t4g)."
  type        = string
  default     = "t4g.large"
}

variable "ec2_root_volume_size" {
  description = "Root EBS volume size in GiB to store Docker volumes and models."
  type        = number
  default     = 80
}

variable "use_spot_instance" {
  description = "Whether to request a spot instance to reduce compute costs."
  type        = bool
  default     = false
}

variable "spot_max_price" {
  description = "Maximum hourly USD price for the spot instance (leave null for on-demand)."
  type        = string
  default     = null
}

variable "budget_notification_emails" {
  description = "Email addresses receiving budget and alarm alerts."
  type        = list(string)

  validation {
    condition     = length(var.budget_notification_emails) > 0
    error_message = "Provide at least one email for budget and alarm notifications."
  }
}

variable "global_budget_monthly_limit" {
  description = "USD limit for the whole AWS account (Harena + Kauri)."
  type        = number
  default     = 30
}

variable "kauri_budget_monthly_limit" {
  description = "USD limit for Kauri-tagged resources only."
  type        = number
  default     = 18
}

variable "base_knowledge_bucket_name" {
  description = "Optional custom bucket name for base connaissances. Leave blank to auto-generate."
  type        = string
  default     = ""
}

variable "ssm_parameters" {
  description = <<-EOT
    Map of SSM Parameter Store entries to create.
    Example:
    {
      "KAURI_OPENAI_API_KEY" = {
        type  = "SecureString"
        value = "placeholder"
      }
    }
  EOT
  type = map(object({
    type  = optional(string, "SecureString")
    value = string
  }))
  default = {}
}

variable "enable_scheduler" {
  description = "Create EventBridge scheduler jobs to start/stop the EC2 instance automatically."
  type        = bool
  default     = true
}

variable "scheduler_timezone" {
  description = "IANA timezone used by the scheduler (e.g. Europe/Paris)."
  type        = string
  default     = "Europe/Paris"
}

variable "scheduler_start_expression" {
  description = "Cron expression for the start schedule (EventBridge format). Leave blank to disable."
  type        = string
  default     = "cron(0 7 ? * MON-FRI *)"
}

variable "scheduler_stop_expression" {
  description = "Cron expression for the stop schedule (EventBridge format). Leave blank to disable."
  type        = string
  default     = "cron(0 21 ? * MON-FRI *)"
}

variable "sns_alert_topic_name" {
  description = "Name for the SNS topic receiving alarms (budget + CloudWatch)."
  type        = string
  default     = "kauri-alerts"
}
