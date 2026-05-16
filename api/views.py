import json
import time
import uuid

from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET

from .models import APIToken
from llm_models.models import LLMModel
from chat import llm as llm_service


# ─────────────────────────────────────────────────────────────────────────────
# Auth helper
# ─────────────────────────────────────────────────────────────────────────────

def _resolve_token(request):
    """Devuelve el APIToken activo del header 'Authorization: Bearer <key>'."""
    auth = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth.startswith('Bearer '):
        return None
    key = auth[7:].strip()
    # Quitar prefijo decorativo si el cliente lo incluye
    if key.startswith('sk-shirka-'):
        key = key[len('sk-shirka-'):]
    try:
        return APIToken.objects.select_related('user').get(key=key, is_active=True)
    except APIToken.DoesNotExist:
        return None


def _unauth():
    return JsonResponse(
        {'error': {'message': 'Invalid API key.', 'type': 'authentication_error', 'code': 'invalid_api_key'}},
        status=401,
    )


# ─────────────────────────────────────────────────────────────────────────────
# /v1/models
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
def v1_list_models(request):
    """GET /v1/models — lista de modelos disponibles en formato OpenAI."""
    token = _resolve_token(request)
    if not token:
        return _unauth()

    models_qs = LLMModel.objects.filter(status__in=['ready', 'active'])
    data = [
        {
            'id': m.catalog_id,
            'object': 'model',
            'created': int(m.created_at.timestamp()),
            'owned_by': 'shirkaai',
            'name': m.name,
            'status': m.status,
        }
        for m in models_qs
    ]
    return JsonResponse({'object': 'list', 'data': data})


# ─────────────────────────────────────────────────────────────────────────────
# /v1/chat/completions
# ─────────────────────────────────────────────────────────────────────────────

@csrf_exempt
def v1_chat_completions(request):
    """POST /v1/chat/completions — genera una respuesta en formato OpenAI."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method Not Allowed'}, status=405)

    token = _resolve_token(request)
    if not token:
        return _unauth()

    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return JsonResponse({'error': {'message': 'Invalid JSON body.', 'type': 'invalid_request_error'}}, status=400)

    model_id     = body.get('model', '')
    messages     = body.get('messages', [])
    max_tokens   = int(body.get('max_tokens', 512))
    temperature  = float(body.get('temperature', 0.7))

    if not messages:
        return JsonResponse({'error': {'message': '`messages` is required.', 'type': 'invalid_request_error'}}, status=400)

    # Buscar modelo por catalog_id
    llm_model = LLMModel.objects.filter(catalog_id=model_id, status__in=['ready', 'active']).first()
    if not llm_model:
        # Intentar con el primero activo como fallback
        llm_model = LLMModel.objects.filter(status='active').first()
    if not llm_model or not llm_model.local_path:
        return JsonResponse(
            {'error': {'message': f'Model "{model_id}" not found or not ready.', 'type': 'invalid_request_error'}},
            status=404,
        )

    try:
        reply = llm_service.generate(
            llm_model.local_path, messages,
            max_tokens=max_tokens, temperature=temperature,
        )
    except Exception as exc:
        return JsonResponse(
            {'error': {'message': str(exc), 'type': 'server_error'}},
            status=500,
        )

    completion_id = f'chatcmpl-{uuid.uuid4().hex[:20]}'
    created_ts    = int(time.time())

    return JsonResponse({
        'id':      completion_id,
        'object':  'chat.completion',
        'created': created_ts,
        'model':   llm_model.catalog_id,
        'choices': [
            {
                'index':         0,
                'message':       {'role': 'assistant', 'content': reply},
                'finish_reason': 'stop',
            }
        ],
        'usage': {
            'prompt_tokens':     sum(len(m.get('content', '').split()) for m in messages),
            'completion_tokens': len(reply.split()),
            'total_tokens':      sum(len(m.get('content', '').split()) for m in messages) + len(reply.split()),
        },
    })


# ─────────────────────────────────────────────────────────────────────────────
# Web: Documentación
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def api_docs(request):
    base_url = request.build_absolute_uri('/').rstrip('/')
    return render(request, 'api/docs.html', {'base_url': base_url})


# ─────────────────────────────────────────────────────────────────────────────
# Web: Gestión de tokens
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def api_tokens(request):
    tokens = APIToken.objects.filter(user=request.user)
    new_token = request.session.pop('new_token_key', None)
    new_token_name = request.session.pop('new_token_name', None)
    return render(request, 'api/tokens.html', {
        'tokens': tokens,
        'new_token': new_token,
        'new_token_name': new_token_name,
    })


@login_required
@require_POST
def create_token(request):
    name = request.POST.get('name', '').strip()
    if not name:
        name = 'Mi token'
    token = APIToken.objects.create(user=request.user, name=name)
    # Guardamos la key en sesión para mostrarla UNA sola vez
    request.session['new_token_key']  = f'sk-shirka-{token.key}'
    request.session['new_token_name'] = token.name
    return redirect('api:tokens')


@login_required
@require_POST
def revoke_token(request, pk):
    token = get_object_or_404(APIToken, pk=pk, user=request.user)
    token.is_active = False
    token.save(update_fields=['is_active'])
    return redirect('api:tokens')
