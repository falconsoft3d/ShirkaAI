# ShirkaAI

Plataforma de asistentes de IA privados y autogestionados. Permite crear proyectos de chat con modelos de lenguaje grandes (LLM) corriendo **localmente** (formato GGUF) o vía **OpenAI**, con soporte de RAG documental, memoria vectorial y una API compatible con OpenAI.

---

## Características principales

| Módulo | Descripción |
|---|---|
| **Modelos LLM** | Descarga y gestiona modelos GGUF desde HuggingFace (Llama, Phi, Qwen, Mistral…) |
| **Proyectos** | Crea proyectos de chat asociados a un modelo local u OpenAI |
| **Chat** | Interfaz conversacional multi-sesión con historial persistente |
| **RAG documental** | Sube PDFs o texto plano; los documentos se vectorizan en ChromaDB para que el LLM los consulte |
| **Memoria vectorial** | El historial de conversaciones se almacena como vectores para recuperar contexto relevante en futuros chats |
| **API REST** | Endpoint compatible con la especificación OpenAI (`/v1/models`, `/v1/chat/completions`) con autenticación por token Bearer |
| **Chat público** | URL pública que permite a visitantes sin cuenta chatear con un modelo expuesto |
| **Gestión de usuarios** | Multi-usuario con roles staff/superusuario y avatar de perfil |
| **Tareas** | Módulo de tareas y ejecuciones vinculables a proyectos |

---

## Stack tecnológico

- **Backend:** Django 6.0.5
- **Inferencia local:** `llama_cpp_python` (modelos GGUF)
- **Vector store:** ChromaDB
- **Parseo de documentos:** pypdf
- **Base de datos:** SQLite (desarrollo) / PostgreSQL (producción)
- **Servidor web:** Gunicorn + Nginx
- **Despliegue:** Docker / Docker Compose

---

## Configuración local

### Requisitos
- Python 3.10+
- pip

### Pasos

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd ShirkaAI

# 2. Crear y activar entorno virtual
python3 -m venv venv
source venv/bin/activate

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Aplicar migraciones
python manage.py migrate

# 5. Crear superusuario
python manage.py createsuperuser

# 6. Levantar el servidor
python manage.py runserver
```

Abre: http://127.0.0.1:8000

---

## Variables de entorno

Crea un archivo `.env` en la raíz del proyecto con las siguientes variables:

```env
SECRET_KEY=tu-clave-secreta
DEBUG=False
ALLOWED_HOSTS=tudominio.com,www.tudominio.com
CSRF_TRUSTED_ORIGINS=https://tudominio.com

# Base de datos (PostgreSQL)
DB_ENGINE=django.db.backends.postgresql
DB_NAME=shirkaai
DB_USER=postgres
DB_PASSWORD=tu-password
DB_HOST=db
DB_PORT=5432
```

---

## Despliegue con Docker

```bash
# Construir e iniciar todos los servicios
docker compose up --build -d
```

Los servicios incluyen:
- `db` — PostgreSQL 16
- `web` — Django + Gunicorn
- `nginx` — Proxy inverso

---

## Rutas disponibles

| Ruta | Descripción |
|---|---|
| `/` | Landing page |
| `/login/` | Iniciar sesión |
| `/dashboard/` | Dashboard (requiere login) |
| `/models/` | Catálogo de modelos LLM |
| `/projects/` | Gestión de proyectos |
| `/chat/` | Interfaz de chat |
| `/docs/` | Documentos RAG del proyecto |
| `/tasks/` | Tareas y ejecuciones |
| `/api/tokens/` | Gestión de tokens API |
| `/v1/models` | API — lista de modelos (OpenAI-compatible) |
| `/v1/chat/completions` | API — completions de chat (OpenAI-compatible) |
| `/chat-publico/<id>/` | Chat público sin autenticación |
| `/admin/` | Panel de administración Django |

---

## API REST (compatible con OpenAI)

Autenticación mediante header `Authorization: Bearer sk-shirka-<token>`.

### Listar modelos
```http
GET /v1/models
Authorization: Bearer sk-shirka-<tu-token>
```

### Generar respuesta
```http
POST /v1/chat/completions
Authorization: Bearer sk-shirka-<tu-token>
Content-Type: application/json

{
  "model": "llama-3.2-1b",
  "messages": [
    {"role": "user", "content": "¿Qué es ShirkaAI?"}
  ],
  "max_tokens": 512,
  "temperature": 0.7
}
```

Los tokens se generan desde `/api/tokens/` en la interfaz web.

---

## Comandos útiles

```bash
# Crear migraciones tras cambiar modelos
python manage.py makemigrations

# Shell interactivo de Django
python manage.py shell

# Levantar en otro puerto
python manage.py runserver 8080

# Correr en red local
python manage.py runserver 0.0.0.0:8000
```
