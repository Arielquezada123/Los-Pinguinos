FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalamos dependencias del sistema necesarias para compilar
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libpcre2-dev \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar proyecto
COPY . /pinguinos
WORKDIR /pinguinos
RUN SECRET_KEY=dummy_value python manage.py collectstatic --noinput --clear
# Crear directorios para static y media
RUN mkdir -p /pinguinos/staticfiles /pinguinos/media

RUN sed -i 's/\r$//g' /pinguinos/entrypoint.sh
# Hacer ejecutable el entrypoint
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
