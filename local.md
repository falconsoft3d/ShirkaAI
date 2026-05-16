# ShirkaAI – Comandos locales

## Requisitos
- Python 3.10+
- pip

---

## 1. Crear entorno virtual
```bash
python3 -m venv venv
```

## 2. Activar entorno virtual
```bash
source venv/bin/activate
```

## 3. Instalar dependencias
```bash
pip install django pillow
```

## 4. Aplicar migraciones
```bash
python manage.py migrate
```

## 5. Crear superusuario
```bash
python manage.py createsuperuser
```
> Credenciales de prueba actuales: `admin` / `admin123`

## 6. Levantar servidor
```bash
python manage.py runserver
```
Abre: http://127.0.0.1:8000

---

## Rutas disponibles

| Ruta | Descripción |
|------|-------------|
| `/` | Home / Landing page |
| `/login/` | Iniciar sesión |
| `/dashboard/` | Dashboard (requiere login) |
| `/logout/` | Cerrar sesión |
| `/admin/` | Panel de administración Django |

---

## Comandos útiles

```bash
# Crear migraciones tras cambiar modelos
python manage.py makemigrations

# Shell interactivo de Django
python manage.py shell

# Ver todas las URLs registradas
python manage.py show_urls 2>/dev/null || python manage.py shell -c "from django.urls import get_resolver; [print(p) for p in get_resolver().url_patterns]"

# Levantar en otro puerto
python manage.py runserver 8080

# Correr en red local (acceso desde otros dispositivos)
python manage.py runserver 0.0.0.0:8000
```
