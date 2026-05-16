from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.utils import timezone
from datetime import timedelta
from llm_models.models import LLMModel
from projects.models import Project
from chat.models import ChatSession, ChatMessage
from .models import UserProfile


def home(request):
    features = [
        {'icon': '🧠', 'title': 'Modelos LLM', 'desc': 'Llama, Mistral, Qwen, DeepSeek y más corriendo localmente.'},
        {'icon': '🔌', 'title': 'Integraciones', 'desc': 'Conecta Odoo, WhatsApp, Gmail, calendarios y ERPs.'},
        {'icon': '💾', 'title': 'Memoria', 'desc': 'Historial, contactos, documentos y preferencias persistentes.'},
        {'icon': '🔒', 'title': 'Privacidad', 'desc': 'Tus datos en tu servidor, sin dependencias de terceros.'},
    ]
    public_models = LLMModel.objects.filter(public=True, status__in=['ready', 'active'])
    return render(request, 'core/home.html', {
        'features': features,
        'public_models': public_models,
    })


@login_required
def dashboard(request):
    now   = timezone.now()
    week  = now - timedelta(days=7)
    month = now - timedelta(days=30)

    user_projects = Project.objects.filter(owner=request.user)
    sessions      = ChatSession.objects.filter(project__owner=request.user)

    stats = {
        'projects_total':      user_projects.count(),
        'projects_with_ai':    user_projects.filter(model__isnull=False).count(),
        'models_total':        LLMModel.objects.count(),
        'models_ready':        LLMModel.objects.filter(status='ready').count(),
        'models_active':       LLMModel.objects.filter(status='active').first(),
        'models_downloading':  LLMModel.objects.filter(status='downloading').count(),
        'sessions_total':      sessions.count(),
        'sessions_week':       sessions.filter(created_at__gte=week).count(),
        'messages_total':      ChatMessage.objects.filter(session__project__owner=request.user).count(),
        'messages_week':       ChatMessage.objects.filter(session__project__owner=request.user, created_at__gte=week).count(),
    }

    recent_projects  = user_projects.order_by('-updated_at')[:5]
    recent_sessions  = sessions.order_by('-updated_at')[:5]

    return render(request, 'core/dashboard.html', {
        'stats':           stats,
        'recent_projects': recent_projects,
        'recent_sessions': recent_sessions,
    })


@login_required
def profile_view(request):
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user)

    if request.method == 'POST':
        username    = request.POST.get('username', '').strip()
        email       = request.POST.get('email', '').strip()
        first_name  = request.POST.get('first_name', '').strip()
        last_name   = request.POST.get('last_name', '').strip()
        current_pwd = request.POST.get('current_password', '').strip()
        new_pwd     = request.POST.get('new_password', '').strip()
        confirm_pwd = request.POST.get('confirm_password', '').strip()
        clear_avatar = request.POST.get('clear_avatar') == '1'

        error = None

        if not username:
            error = 'El nombre de usuario es obligatorio.'
        elif username != user.username and User.objects.filter(username=username).exists():
            error = f'El nombre de usuario "{username}" ya está en uso.'
        elif new_pwd:
            if not user.check_password(current_pwd):
                error = 'La contraseña actual no es correcta.'
            elif new_pwd != confirm_pwd:
                error = 'Las contraseñas nuevas no coinciden.'
            elif len(new_pwd) < 8:
                error = 'La contraseña debe tener al menos 8 caracteres.'

        if error:
            return render(request, 'core/profile.html', {'profile': profile, 'error': error})

        user.username   = username
        user.email      = email
        user.first_name = first_name
        user.last_name  = last_name

        if new_pwd:
            user.set_password(new_pwd)
            update_session_auth_hash(request, user)  # keeps session alive after pwd change

        user.save()

        if clear_avatar and profile.avatar:
            profile.avatar.delete(save=False)
            profile.avatar = None

        if 'avatar' in request.FILES:
            if profile.avatar:
                profile.avatar.delete(save=False)
            profile.avatar = request.FILES['avatar']

        profile.save()
        messages.success(request, 'Perfil actualizado correctamente.')
        return redirect('profile')

    return render(request, 'core/profile.html', {'profile': profile})


# ── Gestión de usuarios ────────────────────────────────────────────────────

def _staff_required(view_fn):
    """Decorador: solo usuarios staff (o superusuario) pueden acceder."""
    from functools import wraps
    from django.http import HttpResponseForbidden

    @login_required
    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_staff:
            return HttpResponseForbidden('No tienes permiso para acceder aquí.')
        return view_fn(request, *args, **kwargs)
    return wrapper


@_staff_required
def user_new(request):
    return render(request, 'core/user_form.html', {})


@_staff_required
def settings_users(request):
    users = User.objects.all().order_by('date_joined')
    return render(request, 'core/settings_users.html', {'users': users})


@_staff_required
@require_POST
def user_create(request):
    username = request.POST.get('username', '').strip()
    email    = request.POST.get('email', '').strip()
    password = request.POST.get('password', '')
    is_staff = request.POST.get('is_staff') == 'on'

    if not username or not password:
        return render(request, 'core/user_form.html', {
            'error': 'El nombre de usuario y la contraseña son obligatorios.',
            'form_username': username,
            'form_email': email,
        })

    if User.objects.filter(username=username).exists():
        return render(request, 'core/user_form.html', {
            'error': f'Ya existe un usuario con el nombre "{username}".',
            'form_username': username,
            'form_email': email,
        })

    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_staff = is_staff
    user.save(update_fields=['is_staff'])
    messages.success(request, f'Usuario "{username}" creado correctamente.')
    return redirect('settings_users')


@_staff_required
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email    = request.POST.get('email', '').strip()
        is_staff = request.POST.get('is_staff') == 'on'
        new_password = request.POST.get('new_password', '').strip()
        confirm_password = request.POST.get('confirm_password', '').strip()

        error = None
        if not username:
            error = 'El nombre de usuario es obligatorio.'
        elif username != user.username and User.objects.filter(username=username).exists():
            error = f'Ya existe un usuario con el nombre "{username}".'
        elif new_password and new_password != confirm_password:
            error = 'Las contraseñas no coinciden.'
        elif new_password and len(new_password) < 8:
            error = 'La contraseña debe tener al menos 8 caracteres.'

        if error:
            return render(request, 'core/user_edit.html', {'u': user, 'error': error})

        user.username = username
        user.email = email
        if not user.is_superuser:
            user.is_staff = is_staff
        if new_password:
            user.set_password(new_password)
        user.save()
        messages.success(request, f'Usuario "{username}" actualizado correctamente.')
        return redirect('settings_users')

    return render(request, 'core/user_edit.html', {'u': user})


@_staff_required
@require_POST
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    if user == request.user:
        request.session['user_error'] = 'No puedes eliminar tu propia cuenta.'
        return redirect('settings_users')
    if user.is_superuser:
        request.session['user_error'] = 'No se puede eliminar a un superusuario.'
        return redirect('settings_users')
    username = user.username
    user.delete()
    messages.success(request, f'Usuario "{username}" eliminado.')
    return redirect('settings_users')


# ── Chat público ───────────────────────────────────────────────────────────

def public_chat(request, pk):
    """Chat público para un modelo marcado como público. No requiere login."""
    model = get_object_or_404(LLMModel, pk=pk, public=True, status__in=['ready', 'active'])
    session_key = f'public_chat_{pk}'
    history = request.session.get(session_key, [])
    return render(request, 'core/public_chat.html', {
        'model': model,
        'history': history,
    })


def public_chat_send(request, pk):
    """Endpoint AJAX para enviar un mensaje al modelo público."""
    from django.http import JsonResponse
    from chat import llm as llm_service

    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido'}, status=405)

    model = get_object_or_404(LLMModel, pk=pk, public=True, status__in=['ready', 'active'])

    content = request.POST.get('message', '').strip()
    if not content:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    session_key = f'public_chat_{pk}'
    history = request.session.get(session_key, [])

    history.append({'role': 'user', 'content': content})

    try:
        llm_messages = [{'role': 'system', 'content': 'Eres un asistente útil y amable.'}] + history
        reply = llm_service.generate(model.local_path, llm_messages)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    history.append({'role': 'assistant', 'content': reply})

    # Conservar máximo los últimos 20 mensajes para no saturar la sesión
    if len(history) > 20:
        history = history[-20:]
    request.session[session_key] = history
    request.session.modified = True

    return JsonResponse({'reply': reply})


def public_chat_clear(request, pk):
    """Limpia el historial de la sesión del chat público."""
    from django.http import JsonResponse
    if request.method == 'POST':
        session_key = f'public_chat_{pk}'
        request.session.pop(session_key, None)
        request.session.modified = True
    return JsonResponse({'ok': True})
