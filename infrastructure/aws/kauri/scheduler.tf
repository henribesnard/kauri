resource "aws_iam_role" "scheduler" {
  count = var.enable_scheduler ? 1 : 0

  name = "${var.project_name}-${var.environment}-scheduler-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "scheduler.amazonaws.com" }
        Action    = "sts:AssumeRole"
      }
    ]
  })

  tags = local.common_tags
}

resource "aws_iam_role_policy" "scheduler" {
  count = var.enable_scheduler ? 1 : 0

  role = aws_iam_role.scheduler[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = [
          "ec2:StartInstances",
          "ec2:StopInstances",
          "ec2:DescribeInstances"
        ]
        Resource = aws_instance.kauri.arn
      }
    ]
  })
}

resource "aws_scheduler_schedule" "start" {
  count = var.enable_scheduler && var.scheduler_start_expression != "" ? 1 : 0

  name        = "${var.project_name}-${var.environment}-start"
  description = "Automatically start the Kauri EC2 host."

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.scheduler_start_expression
  schedule_expression_timezone = var.scheduler_timezone

  target {
    arn      = "arn:${data.aws_partition.current.partition}:scheduler:::aws-sdk:ec2:startInstances"
    role_arn = aws_iam_role.scheduler[0].arn

    input = jsonencode({
      InstanceIds = [aws_instance.kauri.id]
    })
  }

  depends_on = [aws_iam_role_policy.scheduler]
}

resource "aws_scheduler_schedule" "stop" {
  count = var.enable_scheduler && var.scheduler_stop_expression != "" ? 1 : 0

  name        = "${var.project_name}-${var.environment}-stop"
  description = "Automatically stop the Kauri EC2 host."

  flexible_time_window {
    mode = "OFF"
  }

  schedule_expression          = var.scheduler_stop_expression
  schedule_expression_timezone = var.scheduler_timezone

  target {
    arn      = "arn:${data.aws_partition.current.partition}:scheduler:::aws-sdk:ec2:stopInstances"
    role_arn = aws_iam_role.scheduler[0].arn

    input = jsonencode({
      InstanceIds = [aws_instance.kauri.id]
    })
  }

  depends_on = [aws_iam_role_policy.scheduler]
}
