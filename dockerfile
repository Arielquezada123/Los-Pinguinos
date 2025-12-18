FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    libpcre2-dev \
    # Librerías para WeasyPrint 
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libjpeg-dev \
    libopenjp2-7-dev \
    libxcb1 \
    # Librerías para códigos de barras y QR
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install uwsgi

# Copiar proyecto
COPY . /pinguinos
WORKDIR /pinguinos

# Crear directorios para static y media
RUN mkdir -p /pinguinos/staticfiles /pinguinos/media

# Hacer ejecutable el entrypoint
RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
