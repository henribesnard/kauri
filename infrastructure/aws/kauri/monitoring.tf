resource "aws_sns_topic" "alerts" {
  name = var.sns_alert_topic_name

  tags = merge(local.common_tags, { Name = "${var.project_name}-${var.environment}-alerts" })
}

resource "aws_sns_topic_subscription" "alert_emails" {
  for_each = toset(var.budget_notification_emails)

  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = each.value
}

resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "${var.project_name}-${var.environment}-cpu-spike"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 300
  statistic           = "Average"
  threshold           = 85
  alarm_description   = "Notify when EC2 CPU > 85% for 5 minutes."
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    InstanceId = aws_instance.kauri.id
  }
}

resource "aws_cloudwatch_metric_alarm" "status_failed" {
  alarm_name          = "${var.project_name}-${var.environment}-status-check"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "StatusCheckFailed"
  namespace           = "AWS/EC2"
  period              = 60
  statistic           = "Maximum"
  threshold           = 0
  alarm_description   = "Notify when EC2 status checks fail."
  treat_missing_data  = "breaching"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    InstanceId = aws_instance.kauri.id
  }
}

resource "aws_budgets_budget" "global" {
  name              = "${var.project_name}-global-guardrail"
  budget_type       = "COST"
  limit_amount      = var.global_budget_monthly_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2024-01-01_00:00"

  cost_types {
    include_credit             = true
    include_refund             = true
    include_tax                = true
    include_support            = true
    include_subscription       = true
    use_amortized              = true
    use_blended                = false
  }

  dynamic "notification" {
    for_each = toset([60, 80, 100, 110])

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "FORECASTED"
      subscriber_email_addresses = var.budget_notification_emails
      subscriber_sns_topic_arns  = [aws_sns_topic.alerts.arn]
    }
  }
}

resource "aws_budgets_budget" "kauri" {
  name              = "${var.project_name}-tagged-guardrail"
  budget_type       = "COST"
  limit_amount      = var.kauri_budget_monthly_limit
  limit_unit        = "USD"
  time_unit         = "MONTHLY"
  time_period_start = "2024-01-01_00:00"

  cost_filter {
    name = "TagKeyValue"
    values = [
      "Project$${var.project_name}"
    ]
  }

  cost_types {
    include_credit       = true
    include_refund       = true
    include_subscription = true
    use_amortized        = true
  }

  dynamic "notification" {
    for_each = toset([60, 80, 100])

    content {
      comparison_operator        = "GREATER_THAN"
      threshold                  = notification.value
      threshold_type             = "PERCENTAGE"
      notification_type          = "ACTUAL"
      subscriber_email_addresses = var.budget_notification_emails
      subscriber_sns_topic_arns  = [aws_sns_topic.alerts.arn]
    }
  }
}
