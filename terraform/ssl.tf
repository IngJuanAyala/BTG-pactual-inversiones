# ACM Certificate
resource "aws_acm_certificate" "main" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ssl-cert"
  })
}

# Route 53 Zone
resource "aws_route53_zone" "main" {
  name = var.domain_name

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-route53-zone"
  })
}

# DNS Records para validación del certificado
resource "aws_route53_record" "cert_validation" {
  for_each = {
    for dvo in aws_acm_certificate.main.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }

  allow_overwrite = true
  name            = each.value.name
  records         = [each.value.record]
  ttl             = 60
  type            = each.value.type
  zone_id         = aws_route53_zone.main.zone_id
}

# Validación del certificado
resource "aws_acm_certificate_validation" "main" {
  certificate_arn         = aws_acm_certificate.main.arn
  validation_record_fqdns = [for record in aws_route53_record.cert_validation : record.fqdn]
}

# A Record para el ALB
resource "aws_route53_record" "alb" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# Subdominios para cada servicio
resource "aws_route53_record" "auth_service" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "auth.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "funds_service" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "funds.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "notification_service" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "notifications.${var.domain_name}"
  type    = "A"

  alias {
    name                   = aws_lb.main.dns_name
    zone_id                = aws_lb.main.zone_id
    evaluate_target_health = true
  }
}

# Outputs
output "domain_name" {
  description = "Dominio principal"
  value       = var.domain_name
}

output "auth_service_url" {
  description = "URL del servicio de autenticación"
  value       = "https://auth.${var.domain_name}"
}

output "funds_service_url" {
  description = "URL del servicio de fondos"
  value       = "https://funds.${var.domain_name}"
}

output "notification_service_url" {
  description = "URL del servicio de notificaciones"
  value       = "https://notifications.${var.domain_name}"
}

output "nameservers" {
  description = "Nameservers de Route 53"
  value       = aws_route53_zone.main.name_servers
}

