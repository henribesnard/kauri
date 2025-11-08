resource "aws_ssm_parameter" "kauri" {
  for_each = var.ssm_parameters

  name  = "/${var.project_name}/${each.key}"
  type  = each.value.type
  value = each.value.value
  tier  = "Standard"

  tags = local.common_tags
}
