resource "aws_vpc" "kauri" {
  cidr_block           = local.vpc_cidr_block
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = merge(local.common_tags, { Name = "${var.project_name}-${var.environment}-vpc" })
}

resource "aws_internet_gateway" "kauri" {
  vpc_id = aws_vpc.kauri.id

  tags = merge(local.common_tags, { Name = "${var.project_name}-${var.environment}-igw" })
}

resource "aws_subnet" "public_a" {
  vpc_id                  = aws_vpc.kauri.id
  cidr_block              = local.public_subnet_cidr
  map_public_ip_on_launch = true
  availability_zone       = format("%sa", var.aws_region)

  tags = merge(local.common_tags, { Name = "${var.project_name}-${var.environment}-public-a" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.kauri.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.kauri.id
  }

  tags = merge(local.common_tags, { Name = "${var.project_name}-${var.environment}-public-rt" })
}

resource "aws_route_table_association" "public_a" {
  subnet_id      = aws_subnet.public_a.id
  route_table_id = aws_route_table.public.id
}
