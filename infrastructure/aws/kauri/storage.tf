resource "random_string" "bucket_suffix" {
  length  = 5
  upper   = false
  special = false
}

locals {
  base_bucket_name = var.base_knowledge_bucket_name != "" ? var.base_knowledge_bucket_name : "${var.project_name}-${var.environment}-knowledge-${random_string.bucket_suffix.result}"
}

resource "aws_s3_bucket" "base_connaissances" {
  bucket        = local.base_bucket_name
  force_destroy = false

  tags = merge(local.common_tags, { Name = "${var.project_name}-${var.environment}-knowledge" })
}

resource "aws_s3_bucket_versioning" "base_connaissances" {
  bucket = aws_s3_bucket.base_connaissances.id

  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "base_connaissances" {
  bucket = aws_s3_bucket.base_connaissances.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "base_connaissances" {
  bucket                  = aws_s3_bucket.base_connaissances.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_lifecycle_configuration" "base_connaissances" {
  bucket = aws_s3_bucket.base_connaissances.id

  rule {
    id     = "glacier-archive"
    status = "Enabled"

    filter {
      prefix = "dumps/"
    }

    transition {
      days          = 7
      storage_class = "GLACIER_IR"
    }
  }
}
