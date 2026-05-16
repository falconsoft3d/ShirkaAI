# ShirkaAI – Guía de despliegue en Ubuntu con Docker, Nginx y HTTPS

## Requisitos del servidor
- Ubuntu 22.04 / 24.04 LTS
- Mínimo 2 GB RAM (4 GB recomendado si vas a usar modelos LLM)
- Dominio apuntando a la IP del servidor (registro A en tu DNS)

---

## 1. Preparar el servidor

```bash
# Actualizar el sistema
sudo apt update && sudo apt upgrade -y

# Instalar dependencias base
sudo apt install -y git curl ca-certificates gnupg
```

---

## 2. Instalar Docker y Docker Compose

```bash
# Añadir repositorio oficial de Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
  | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Añadir tu usuario al grupo docker (para no usar sudo siempre)
sudo usermod -aG docker $USER
newgrp docker

# Verificar instalación
docker --version
docker compose version
```

---

## 3. Clonar el proyecto

```bash
cd /opt
sudo git clone https://github.com/TU_USUARIO/ShirkaAI.git shirkaai
sudo chown -R $USER:$USER /opt/shirkaai
cd /opt/shirkaai
```

---

## 4. Crear el archivo .env

```bash
cp .env.example .env
nano .env
```

Edita los valores en `.env`:

```env
SECRET_KEY=genera-una-clave-con-el-comando-de-abajo
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com,https://www.tudominio.com

DB_ENGINE=django.db.backends.postgresql
DB_NAME=shirkaai
DB_USER=shirkaai_user
DB_PASSWORD=una-password-muy-segura
DB_HOST=db
DB_PORT=5432
```

Generar una SECRET_KEY segura:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

---

## 5. Configurar el dominio en Nginx

```bash
# Reemplaza TU_DOMINIO.COM con tu dominio real
sed -i 's/TU_DOMINIO.COM/tudominio.com/g' nginx/nginx.conf
```

---

## 6. Obtener certificado SSL (Let's Encrypt)

### Paso 6a — Arrancar solo Nginx en modo HTTP (sin SSL todavía)

Comenta temporalmente el bloque HTTPS del `nginx/nginx.conf` y deja solo el bloque HTTP:

```bash
# Edita el archivo y comenta desde "# ── HTTPS" hasta el final
nano nginx/nginx.conf
```

Arranca los servicios:
```bash
docker compose up -d db nginx
```

### Paso 6b — Solicitar el certificado

```bash
docker compose run --rm certbot certonly \
  --webroot \
  --webroot-path /var/www/certbot \
  --email tu@email.com \
  --agree-tos \
  --no-eff-email \
  -d tudominio.com \
  -d www.tudominio.com
```

### Paso 6c — Descargar configuración SSL recomendada de Certbot

```bash
docker compose exec nginx sh -c "
  curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
    > /etc/letsencrypt/options-ssl-nginx.conf
  openssl dhparam -out /etc/letsencrypt/ssl-dhparams.pem 2048
"
```

### Paso 6d — Restaurar el nginx.conf completo con HTTPS

```bash
# Descomenta el bloque HTTPS que comentaste antes
nano nginx/nginx.conf
```

---

## 7. Arrancar todos los servicios

```bash
docker compose up -d
```

Verificar que todo esté corriendo:
```bash
docker compose ps
docker compose logs -f web
```

---

## 8. Crear superusuario

```bash
docker compose exec web python manage.py createsuperuser
```

---

## 9. (Opcional) Subir un modelo LLM

Los modelos `.gguf` van en el volumen `models_data`. Para copiar uno desde tu máquina local:

```bash
# Desde tu máquina local
scp Phi-3-mini-4k-instruct-q4.gguf usuario@tuservidor:/tmp/

# Desde el servidor
docker compose cp /tmp/Phi-3-mini-4k-instruct-q4.gguf web:/app/media/models/phi3-mini/
```

---

## 10. Renovación automática del certificado SSL

El servicio `certbot` en `docker-compose.yml` renueva automáticamente cada 12 horas.
Para forzar la renovación manualmente:

```bash
docker compose run --rm certbot renew
docker compose exec nginx nginx -s reload
```

---

## Comandos útiles

```bash
# Ver logs en tiempo real
docker compose logs -f

# Ver logs solo de Django
docker compose logs -f web

# Reiniciar un servicio
docker compose restart web

# Parar todo
docker compose down

# Parar y eliminar volúmenes (¡CUIDADO! borra la base de datos)
docker compose down -v

# Actualizar el código
git pull
docker compose build web
docker compose up -d web

# Ejecutar migraciones manualmente
docker compose exec web python manage.py migrate

# Shell de Django
docker compose exec web python manage.py shell

# Backup de la base de datos
docker compose exec db pg_dump -U shirkaai_user shirkaai > backup_$(date +%Y%m%d).sql

# Restaurar backup
cat backup_20260101.sql | docker compose exec -T db psql -U shirkaai_user shirkaai
```

---

## Estructura de archivos Docker

```
ShirkaAI/
├── Dockerfile              # Imagen de la app Django
├── docker-compose.yml      # Orquestación de servicios
├── .env                    # Variables de entorno (NO subir a git)
├── .env.example            # Plantilla de variables
├── requirements.txt        # Dependencias Python
└── nginx/
    └── nginx.conf          # Configuración de Nginx + SSL
```

---

## Puertos y servicios

| Servicio  | Puerto externo | Puerto interno | Descripción         |
|-----------|---------------|----------------|---------------------|
| Nginx     | 80, 443       | —              | Proxy inverso + SSL |
| Django    | —             | 8000           | Solo accesible por Nginx |
| PostgreSQL| —             | 5432           | Solo accesible internamente |
