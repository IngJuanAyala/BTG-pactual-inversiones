# Usar imagen base de Python
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivo de dependencias
COPY ../requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código del auth-service
COPY . .

# Crear usuario no root para seguridad
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# Exponer puerto
EXPOSE 8002

# Comando por defecto
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8002"]
