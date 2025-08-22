# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-ecs-cluster"
  })
}

# ECR Repositories
resource "aws_ecr_repository" "auth_service" {
  name                 = "${local.name_prefix}-auth-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-auth-service-ecr"
  })
}

resource "aws_ecr_repository" "funds_service" {
  name                 = "${local.name_prefix}-funds-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-funds-service-ecr"
  })
}

resource "aws_ecr_repository" "notification_service" {
  name                 = "${local.name_prefix}-notification-service"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-notification-service-ecr"
  })
}

# Task Definitions (versión económica)
resource "aws_ecs_task_definition" "auth_service" {
  family                   = "${local.name_prefix}-auth-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "auth-service"
      image = "${aws_ecr_repository.auth_service.repository_url}:latest"
      command = ["python", "-m", "uvicorn", "auth-service.main:app", "--host", "0.0.0.0", "--port", "8002"]
      portMappings = [
        {
          containerPort = 8002
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "MONGODB_URL"
          value = var.mongodb_atlas_connection_string
        },
        {
          name  = "REDIS_URL"
          value = "redis://localhost:6379"
        },
        {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.auth_service.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-auth-service-task"
  })
}

resource "aws_ecs_task_definition" "funds_service" {
  family                   = "${local.name_prefix}-funds-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "funds-service"
      image = "${aws_ecr_repository.funds_service.repository_url}:latest"
      command = ["sh", "-c", "cd funds-service && PYTHONPATH=/app python -m uvicorn main:app --host 0.0.0.0 --port 8003"]
      portMappings = [
        {
          containerPort = 8003
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "MONGODB_URL"
          value = var.mongodb_atlas_connection_string
        },
        {
          name  = "REDIS_URL"
          value = "redis://localhost:6379"
        },
        {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.funds_service.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-funds-service-task"
  })
}

resource "aws_ecs_task_definition" "notification_service" {
  family                   = "${local.name_prefix}-notification-service"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
  task_role_arn            = aws_iam_role.ecs_task_role.arn

  container_definitions = jsonencode([
    {
      name  = "notification-service"
      image = "${aws_ecr_repository.notification_service.repository_url}:latest"
      command = ["sh", "-c", "cd notification-service && PYTHONPATH=/app python -m uvicorn main:app --host 0.0.0.0 --port 8001"]
      portMappings = [
        {
          containerPort = 8001
          protocol      = "tcp"
        }
      ]
      environment = [
        {
          name  = "MONGODB_URL"
          value = var.mongodb_atlas_connection_string
        },
        {
          name  = "REDIS_URL"
          value = "redis://localhost:6379"
        },
        {
          name  = "JWT_SECRET_KEY"
          value = var.jwt_secret_key
        },
        {
          name  = "SENDGRID_API_KEY"
          value = var.sendgrid_api_key
        },
        {
          name  = "TWILIO_ACCOUNT_SID"
          value = var.twilio_account_sid
        },
        {
          name  = "TWILIO_AUTH_TOKEN"
          value = var.twilio_auth_token
        },
        {
          name  = "TWILIO_PHONE_NUMBER"
          value = var.twilio_phone_number
        },
        {
          name  = "FROM_EMAIL"
          value = var.from_email
        }
      ]
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.notification_service.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
    }
  ])

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-notification-service-task"
  })
}

# ECS Services (versión económica - solo 1 instancia por servicio)
resource "aws_ecs_service" "auth_service" {
  name            = "${local.name_prefix}-auth-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.auth_service.arn
  desired_count   = 1  # Solo 1 instancia para ahorrar costos
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.auth_service.arn
    container_name   = "auth-service"
    container_port   = 8002
  }

  # depends_on = [aws_lb_listener.https]  # Temporarily commented out

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-auth-service"
  })
}

resource "aws_ecs_service" "funds_service" {
  name            = "${local.name_prefix}-funds-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.funds_service.arn
  desired_count   = 1  # Solo 1 instancia para ahorrar costos
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.funds_service.arn
    container_name   = "funds-service"
    container_port   = 8003
  }

  # depends_on = [aws_lb_listener.https]  # Temporarily commented out

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-funds-service"
  })
}

resource "aws_ecs_service" "notification_service" {
  name            = "${local.name_prefix}-notification-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.notification_service.arn
  desired_count   = 1  # Solo 1 instancia para ahorrar costos
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.ecs.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.notification_service.arn
    container_name   = "notification-service"
    container_port   = 8001
  }

  # depends_on = [aws_lb_listener.https]  # Temporarily commented out

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-notification-service"
  })
}

# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "auth_service" {
  name              = "/ecs/${local.name_prefix}-auth-service"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-auth-service-logs"
  })
}

resource "aws_cloudwatch_log_group" "funds_service" {
  name              = "/ecs/${local.name_prefix}-funds-service"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-funds-service-logs"
  })
}

resource "aws_cloudwatch_log_group" "notification_service" {
  name              = "/ecs/${local.name_prefix}-notification-service"
  retention_in_days = 7

  tags = merge(local.common_tags, {
    Name = "${local.name_prefix}-notification-service-logs"
  })
}

# Outputs para ECR
output "ecr_auth_repository_url" {
  description = "URL del repositorio ECR para Auth Service"
  value       = aws_ecr_repository.auth_service.repository_url
}

output "ecr_funds_repository_url" {
  description = "URL del repositorio ECR para Funds Service"
  value       = aws_ecr_repository.funds_service.repository_url
}

output "ecr_notification_repository_url" {
  description = "URL del repositorio ECR para Notification Service"
  value       = aws_ecr_repository.notification_service.repository_url
}
