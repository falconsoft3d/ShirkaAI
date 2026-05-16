import os
import time
import threading
import requests as http_client
from pathlib import Path

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings
from django.db import connection

from .models import LLMModel

# ── In-memory progress store (reset on server restart) ─────────────────────
_progress = {}       # { db_id: {progress, downloaded, total, speed, status, error} }
_cancel   = {}       # { db_id: threading.Event }

# ── Catálogo de modelos open-source ────────────────────────────────────────
CATALOG = [
    {
        'catalog_id': 'qwen2.5-0.5b',
        'name': 'Qwen 2.5 0.5B',
        'description': 'Ultra-ligero de Alibaba. Ideal para pruebas con poca RAM.',
        'repo_id': 'Qwen/Qwen2.5-0.5B-Instruct-GGUF',
        'filename': 'qwen2.5-0.5b-instruct-q4_k_m.gguf',
        'size_label': '~0.4 GB',
        'tags': 'Qwen,Instruct,Ligero',
        'color': 'blue',
    },
    {
        'catalog_id': 'qwen2.5-1.5b',
        'name': 'Qwen 2.5 1.5B',
        'description': 'Equilibrio perfecto entre tamaño y capacidad de Alibaba.',
        'repo_id': 'Qwen/Qwen2.5-1.5B-Instruct-GGUF',
        'filename': 'qwen2.5-1.5b-instruct-q4_k_m.gguf',
        'size_label': '~1.0 GB',
        'tags': 'Qwen,Instruct',
        'color': 'blue',
    },
    {
        'catalog_id': 'llama-3.2-1b',
        'name': 'Llama 3.2 1B',
        'description': 'Modelo compacto de Meta. Buen punto de partida para tareas simples.',
        'repo_id': 'bartowski/Llama-3.2-1B-Instruct-GGUF',
        'filename': 'Llama-3.2-1B-Instruct-Q4_K_M.gguf',
        'size_label': '~0.8 GB',
        'tags': 'Meta,Instruct,Ligero',
        'color': 'purple',
    },
    {
        'catalog_id': 'llama-3.2-3b',
        'name': 'Llama 3.2 3B',
        'description': 'Mayor capacidad que 1B, sigue siendo ligero. De Meta.',
        'repo_id': 'bartowski/Llama-3.2-3B-Instruct-GGUF',
        'filename': 'Llama-3.2-3B-Instruct-Q4_K_M.gguf',
        'size_label': '~2.0 GB',
        'tags': 'Meta,Instruct',
        'color': 'purple',
    },
    {
        'catalog_id': 'deepseek-r1-1.5b',
        'name': 'DeepSeek R1 1.5B',
        'description': 'Modelo de razonamiento de DeepSeek, versión distilada ligera.',
        'repo_id': 'bartowski/DeepSeek-R1-Distill-Qwen-1.5B-GGUF',
        'filename': 'DeepSeek-R1-Distill-Qwen-1.5B-Q4_K_M.gguf',
        'size_label': '~1.0 GB',
        'tags': 'DeepSeek,Razonamiento',
        'color': 'green',
    },
    {
        'catalog_id': 'phi3-mini',
        'name': 'Phi-3 Mini 3.8B',
        'description': 'Pequeño pero potente, de Microsoft. Excelente para razonamiento.',
        'repo_id': 'microsoft/Phi-3-mini-4k-instruct-gguf',
        'filename': 'Phi-3-mini-4k-instruct-q4.gguf',
        'size_label': '~2.2 GB',
        'tags': 'Microsoft,Razonamiento',
        'color': 'orange',
    },
    {
        'catalog_id': 'mistral-7b',
        'name': 'Mistral 7B',
        'description': 'Modelo 7B de Mistral AI. Excelente para tareas complejas.',
        'repo_id': 'TheBloke/Mistral-7B-Instruct-v0.2-GGUF',
        'filename': 'mistral-7b-instruct-v0.2.Q4_K_M.gguf',
        'size_label': '~4.4 GB',
        'tags': 'Mistral,Instruct',
        'color': 'pink',
    },
]

_CATALOG_MAP = {e['catalog_id']: e for e in CATALOG}


# ── Download worker (background thread) ───────────────────────────────────
def _download_worker(db_id, repo_id, filename, dest_dir):
    """Downloads a GGUF file from HuggingFace with live progress tracking."""
    connection.close()  # avoid sharing parent thread's DB connection

    _progress[db_id] = {
        'progress': 0, 'downloaded': 0, 'total': 0,
        'speed': '', 'status': 'downloading', 'error': '',
    }
    cancel_ev = _cancel.get(db_id)

    dest_path = Path(dest_dir) / filename
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        url = f"https://huggingface.co/{repo_id}/resolve/main/{filename}"
        resp = http_client.get(url, stream=True, timeout=30, allow_redirects=True)
        resp.raise_for_status()

        total = int(resp.headers.get('content-length', 0))
        downloaded = 0
        t0 = time.time()

        with open(dest_path, 'wb') as fh:
            for chunk in resp.iter_content(chunk_size=65536):
                if cancel_ev and cancel_ev.is_set():
                    LLMModel.objects.filter(id=db_id).update(
                        status=LLMModel.STATUS_ERROR,
                        error_message='Descarga cancelada por el usuario',
                    )
                    dest_path.unlink(missing_ok=True)
                    _progress[db_id]['status'] = 'error'
                    return

                if chunk:
                    fh.write(chunk)
                    downloaded += len(chunk)
                    elapsed = time.time() - t0 or 0.001
                    speed = downloaded / elapsed
                    progress = int(downloaded * 100 / total) if total else 0

                    speed_label = (
                        f"{speed / 1_048_576:.1f} MB/s"
                        if speed >= 1_048_576
                        else f"{speed / 1024:.0f} KB/s"
                    )
                    dl_mb   = downloaded / 1_048_576
                    total_mb = total / 1_048_576

                    _progress[db_id].update({
                        'progress': progress,
                        'downloaded': downloaded,
                        'total': total,
                        'speed': speed_label,
                        'dl_mb': f"{dl_mb:.1f}",
                        'total_mb': f"{total_mb:.1f}",
                    })

        LLMModel.objects.filter(id=db_id).update(
            status=LLMModel.STATUS_READY,
            progress=100,
            local_path=str(dest_path),
        )
        _progress[db_id].update({'status': 'ready', 'progress': 100})

    except Exception as exc:
        msg = str(exc)[:500]
        LLMModel.objects.filter(id=db_id).update(
            status=LLMModel.STATUS_ERROR,
            error_message=msg,
        )
        _progress[db_id].update({'status': 'error', 'error': msg})
        if dest_path.exists():
            dest_path.unlink(missing_ok=True)


# ── Views ──────────────────────────────────────────────────────────────────

@login_required
def catalog(request):
    db_map = {m.catalog_id: m for m in LLMModel.objects.all()}

    # Fix stuck 'downloading' models after server restart
    for m in db_map.values():
        if m.status == LLMModel.STATUS_DOWNLOADING and m.id not in _progress:
            m.status = LLMModel.STATUS_ERROR
            m.error_message = 'Descarga interrumpida (servidor reiniciado)'
            m.save(update_fields=['status', 'error_message'])

    items = [
        {
            'entry':     e,
            'db':        db_map.get(e['catalog_id']),
            'tags_list': [t.strip() for t in e['tags'].split(',') if t.strip()],
        }
        for e in CATALOG
    ]
    return render(request, 'llm_models/catalog.html', {'items': items})


@login_required
@require_POST
def download_start(request, catalog_id):
    entry = _CATALOG_MAP.get(catalog_id)
    if not entry:
        return JsonResponse({'error': 'Modelo no encontrado'}, status=404)

    obj, created = LLMModel.objects.get_or_create(
        catalog_id=catalog_id,
        defaults={
            'name':        entry['name'],
            'repo_id':     entry['repo_id'],
            'filename':    entry['filename'],
            'description': entry['description'],
            'size_label':  entry['size_label'],
            'tags':        entry['tags'],
            'status':      LLMModel.STATUS_DOWNLOADING,
        },
    )
    if not created:
        if obj.status in (LLMModel.STATUS_READY, LLMModel.STATUS_ACTIVE):
            return JsonResponse({'error': 'Ya descargado'}, status=400)
        obj.status = LLMModel.STATUS_DOWNLOADING
        obj.progress = 0
        obj.error_message = ''
        obj.save(update_fields=['status', 'progress', 'error_message'])

    dest_dir = os.path.join(settings.MEDIA_ROOT, 'models', catalog_id)
    ev = threading.Event()
    _cancel[obj.id] = ev

    threading.Thread(
        target=_download_worker,
        args=(obj.id, entry['repo_id'], entry['filename'], dest_dir),
        daemon=True,
    ).start()

    return JsonResponse({'model_id': obj.id, 'status': 'downloading'})


@login_required
def download_progress_api(request, model_id):
    obj = get_object_or_404(LLMModel, id=model_id)
    prog = _progress.get(obj.id, {})
    return JsonResponse({
        'model_id':  model_id,
        'status':    prog.get('status', obj.status),
        'progress':  prog.get('progress', obj.progress),
        'speed':     prog.get('speed', ''),
        'dl_mb':     prog.get('dl_mb', '0'),
        'total_mb':  prog.get('total_mb', '0'),
        'error':     prog.get('error', obj.error_message),
    })


@login_required
@require_POST
def activate_model(request, model_id):
    obj = get_object_or_404(LLMModel, id=model_id)
    if obj.status not in (LLMModel.STATUS_READY, LLMModel.STATUS_ACTIVE):
        return JsonResponse({'error': 'Modelo no disponible'}, status=400)
    LLMModel.objects.filter(status=LLMModel.STATUS_ACTIVE).update(status=LLMModel.STATUS_READY)
    obj.status = LLMModel.STATUS_ACTIVE
    obj.save(update_fields=['status'])
    return JsonResponse({'status': 'active'})


@login_required
@require_POST
def deactivate_model(request, model_id):
    obj = get_object_or_404(LLMModel, id=model_id)
    if obj.status == LLMModel.STATUS_ACTIVE:
        obj.status = LLMModel.STATUS_READY
        obj.save(update_fields=['status'])
    return JsonResponse({'status': 'ready'})


@login_required
@require_POST
def toggle_public(request, model_id):
    obj = get_object_or_404(LLMModel, id=model_id)
    if obj.status not in (LLMModel.STATUS_READY, LLMModel.STATUS_ACTIVE):
        return JsonResponse({'error': 'Solo se puede publicar modelos listos o activos'}, status=400)
    obj.public = not obj.public
    obj.save(update_fields=['public'])
    return JsonResponse({'public': obj.public})


@login_required
@require_POST
def delete_model(request, model_id):
    obj = get_object_or_404(LLMModel, id=model_id)
    ev = _cancel.get(obj.id)
    if ev:
        ev.set()
    if obj.local_path and os.path.exists(obj.local_path):
        os.remove(obj.local_path)
    obj.delete()
    return JsonResponse({'status': 'deleted'})

