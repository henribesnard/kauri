data "aws_caller_identity" "current" {}

data "aws_partition" "current" {}

locals {
  vpc_cidr_block    = "10.42.0.0/20"
  public_subnet_cidr = "10.42.1.0/24"

  common_tags = merge(
    {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    },
    var.additional_tags
  )
}
