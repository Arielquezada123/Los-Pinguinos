FROM python:3.12-alpine

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Dependencias del sistema
RUN apk add --no-cache \
    build-base \
    linux-headers \
    gcc \
    musl-dev \
    libc-dev \
    libffi-dev \
    pcre-dev

# Copiar y instalar dependencias Python
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt
RUN pip install uwsgi

# Copiar proyecto
COPY . /pinguinos
WORKDIR /pinguinos

# Collect static
RUN python manage.py collectstatic --noinput

# Exponer puerto HTTP de uWSGI
EXPOSE 8000

CMD ["uwsgi", "--ini", "uwsgi/start_uwsgi.ini"]
