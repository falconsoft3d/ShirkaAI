from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.db.models import Q
import threading
from projects.models import Project
from .models import ChatSession, ChatMessage
from . import llm as llm_service


@login_required
def chat_home(request):
    """Lista de proyectos listos para chatear (local o OpenAI)."""
    projects = (
        Project.objects
        .filter(owner=request.user)
        .filter(
            Q(api_provider='openai', api_key__gt='') |
            Q(api_provider='local', model__status__in=['ready', 'active'])
        )
        .select_related('model')
    )
    return render(request, 'chat/home.html', {'projects': projects})


@login_required
def chat_session(request, project_pk, session_pk=None):
    """Abre o crea una sesión de chat para un proyecto."""
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    if not project.is_chat_ready:
        return redirect('chat:home')

    sessions = project.sessions.all()
    if session_pk:
        session = get_object_or_404(ChatSession, pk=session_pk, project=project)
    elif sessions.exists():
        session = sessions.first()
    else:
        session = ChatSession.objects.create(project=project, title='Nueva conversación')

    messages = session.messages.all()
    return render(request, 'chat/session.html', {
        'project': project,
        'sessions': sessions,
        'session': session,
        'messages': messages,
    })


@login_required
@require_POST
def chat_new_session(request, project_pk):
    project = get_object_or_404(Project, pk=project_pk, owner=request.user)
    if not project.is_chat_ready:
        return redirect('chat:home')
    session = ChatSession.objects.create(project=project, title='Nueva conversación')
    return redirect('chat:session', project_pk=project.pk, session_pk=session.pk)


@login_required
@require_POST
def chat_send(request, session_pk):
    session = get_object_or_404(
        ChatSession, pk=session_pk, project__owner=request.user
    )
    content = request.POST.get('message', '').strip()
    if not content:
        return JsonResponse({'error': 'Mensaje vacío'}, status=400)

    # Guardar mensaje del usuario
    ChatMessage.objects.create(session=session, role='user', content=content)

    # Auto-título en primer mensaje
    if session.messages.count() == 1:
        session.title = content[:60]
        session.save(update_fields=['title', 'updated_at'])

    # Construir historial para el LLM
    history = [
        {'role': msg.role, 'content': msg.content}
        for msg in session.messages.all()
    ]

    project = session.project

    # ── RAG: recuperar contexto documental del proyecto ───────────────────────
    try:
        from docs.embeddings import retrieve_context, retrieve_memory
        context_chunks = retrieve_context(project.pk, content, n_results=5)
        memory_chunks  = retrieve_memory(project.pk, content, n_results=3)
    except Exception:
        context_chunks = []
        memory_chunks  = []

    # Construir system prompt según si hay documentación indexada
    if context_chunks:
        context_text = '\n\n---\n\n'.join(
            f'[Fuente: {c["title"]}]\n{c["text"]}' for c in context_chunks
        )
        system_content = (
            'Eres un asistente de IA experto y preciso. '
            'Responde SIEMPRE basándote principalmente en la documentación del proyecto '
            'que se proporciona a continuación. '
            'Si la respuesta está en la documentación, cítala o resúmela. '
            'Si la pregunta no tiene relación con la documentación, '
            'responde con tu conocimiento general pero indícalo.\n\n'
            '═══════════════════════════════════════\n'
            'DOCUMENTACIÓN DEL PROYECTO\n'
            '═══════════════════════════════════════\n'
            f'{context_text}\n'
            '═══════════════════════════════════════'
        )
    else:
        system_content = (
            'Eres un asistente de IA útil y preciso. '
            'Este proyecto aún no tiene documentación indexada, '
            'así que responde con tu conocimiento general.'
        )

    # Añadir memoria de conversaciones previas relevantes
    if memory_chunks:
        memory_text = '\n\n---\n\n'.join(c['text'] for c in memory_chunks)
        system_content += (
            '\n\n'
            '═══════════════════════════════════════\n'
            'MEMORIA DE CONVERSACIONES PREVIAS\n'
            '═══════════════════════════════════════\n'
            f'{memory_text}\n'
            '═══════════════════════════════════════'
        )

    system_msg = {'role': 'system', 'content': system_content}
    # El historial ya incluye el mensaje del usuario recién guardado
    messages_for_llm = [system_msg] + history

    # ── Routing: OpenAI vs modelo local ───────────────────────────────────
    if project.api_provider == 'openai':
        if not project.api_key:
            return JsonResponse({'error': 'El proyecto no tiene API key configurada.'}, status=400)
        try:
            reply = llm_service.generate_openai(
                api_key=project.api_key,
                model_name=project.api_model_name or 'gpt-4o-mini',
                messages=messages_for_llm,
            )
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=500)
    else:
        model = project.model
        if not model or not model.local_path:
            return JsonResponse({'error': 'El proyecto no tiene un modelo descargado.'}, status=400)
        try:
            reply = llm_service.generate(model.local_path, messages_for_llm)
        except Exception as exc:
            return JsonResponse({'error': str(exc)}, status=500)

    # Guardar respuesta
    msg = ChatMessage.objects.create(session=session, role='assistant', content=reply)
    session.save(update_fields=['updated_at'])

    # Vectorizar el intercambio como memoria en segundo plano
    try:
        from docs.embeddings import store_memory
        threading.Thread(
            target=store_memory,
            args=(project.pk, session.pk, msg.pk, content, reply),
            daemon=True,
        ).start()
    except Exception:
        pass

    return JsonResponse({
        'reply': reply,
        'session_title': session.title,
        'message_id': msg.pk,
    })


@login_required
@require_POST
def chat_delete_session(request, session_pk):
    session = get_object_or_404(ChatSession, pk=session_pk, project__owner=request.user)
    project_pk = session.project_id
    session.delete()
    return redirect('chat:project', project_pk=project_pk)
