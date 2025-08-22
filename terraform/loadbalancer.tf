# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-alb"
  })
}

# Target Groups
resource "aws_lb_target_group" "auth_service" {
  name        = "${local.name_prefix}-auth-tg"
  port        = 8002
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  # Path rewriting configuration
  stickiness {
    type            = "lb_cookie"
    cookie_duration = 86400
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-auth-tg"
  })
}

resource "aws_lb_target_group" "funds_service" {
  name        = "${local.name_prefix}-funds-tg"
  port        = 8003
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-funds-tg"
  })
}

resource "aws_lb_target_group" "notification_service" {
  name        = "${local.name_prefix}-notif-tg"
  port        = 8001
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 2
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-notification-tg"
  })
}

# Listeners
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"

  default_action {
    type = "fixed-response"
    fixed_response {
      content_type = "text/plain"
      message_body = "Not Found - Use /health, /auth/, /funds/, or /notifications/"
      status_code  = "404"
    }
  }
}

# Temporarily commented out due to SSL certificate validation issues
# resource "aws_lb_listener" "https" {
#   load_balancer_arn = aws_lb.main.arn
#   port              = "443"
#   protocol          = "HTTPS"
#   ssl_policy        = "ELBSecurityPolicy-2016-08"
#   certificate_arn   = aws_acm_certificate.main.arn
#
#   default_action {
#     type = "fixed-response"
#     fixed_response {
#       content_type = "text/plain"
#       message_body = "Not Found"
#       status_code  = "404"
#     }
#   }
# }

# Listener Rules - Temporarily commented out due to SSL certificate validation issues
# resource "aws_lb_listener_rule" "auth_service" {
#   listener_arn = aws_lb_listener.https.arn
#   priority     = 100
#
#   action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.auth_service.arn
#   }
#
#   condition {
#     path_pattern {
#       values = ["/auth/*"]
#     }
#   }
# }
#
# resource "aws_lb_listener_rule" "funds_service" {
#   listener_arn = aws_lb_listener.https.arn
#   priority     = 200
#
#   action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.funds_service.arn
#   }
#
#   condition {
#     path_pattern {
#       values = ["/funds/*"]
#     }
#   }
# }
#
# resource "aws_lb_listener_rule" "notification_service" {
#   listener_arn = aws_lb_listener.https.arn
#   priority     = 300
#
#   action {
#     type             = "forward"
#     target_group_arn = aws_lb_target_group.notification_service.arn
#   }
#
#   condition {
#     path_pattern {
#     values = ["/notifications/*"]
#     }
#   }
# }

# Listener Rules for HTTP (temporary until SSL is configured)
resource "aws_lb_listener_rule" "health_check" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 50

  action {
    type = "forward"
    target_group_arn = aws_lb_target_group.auth_service.arn
  }

  condition {
    path_pattern {
      values = ["/health"]
    }
  }
}

resource "aws_lb_listener_rule" "auth_service" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 100

  action {
    type = "forward"
    target_group_arn = aws_lb_target_group.auth_service.arn
  }

  condition {
    path_pattern {
      values = ["/auth", "/auth/*"]
    }
  }
}

# Regla específica para reescribir rutas del auth service
resource "aws_lb_listener_rule" "auth_rewrite" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 90

  action {
    type = "forward"
    target_group_arn = aws_lb_target_group.auth_service.arn
  }

  condition {
    path_pattern {
      values = ["/auth/health", "/auth/docs", "/auth/openapi.json"]
    }
  }
}

# Regla específica para la documentación de Swagger
resource "aws_lb_listener_rule" "swagger_docs" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 85

  action {
    type = "forward"
    target_group_arn = aws_lb_target_group.auth_service.arn
  }

  condition {
    path_pattern {
      values = ["/docs", "/redoc", "/openapi.json"]
    }
  }
}

resource "aws_lb_listener_rule" "funds_service" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 200

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.funds_service.arn
  }

  condition {
    path_pattern {
      values = ["/funds/*"]
    }
  }
}

resource "aws_lb_listener_rule" "notification_service" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 300

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.notification_service.arn
  }

  condition {
    path_pattern {
      values = ["/notifications/*"]
    }
  }
}

# Outputs
output "alb_dns_name" {
  description = "DNS name del Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID del Application Load Balancer"
  value       = aws_lb.main.zone_id
}

