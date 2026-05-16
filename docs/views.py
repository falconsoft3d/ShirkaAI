import threading
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from projects.models import Project
from .models import ProjectDocument
from . import embeddings as rag

# ── Eventos de pausa por doc_id (vivo mientras el thread existe) ──────────────
_pause_events: dict[int, threading.Event] = {}


# ── Worker de indexación en segundo plano ─────────────────────────────────────

def _index_worker(doc_id: int, pause_event: threading.Event) -> None:
    """Corre en un thread separado: indexa el documento y actualiza su estado."""
    try:
        doc = ProjectDocument.objects.get(pk=doc_id)
        ProjectDocument.objects.filter(pk=doc_id).update(
            index_status='indexing', index_error='', index_progress=0
        )

        def on_progress(pct, processed, total):
            ProjectDocument.objects.filter(pk=doc_id).update(index_progress=pct)
            pause_event.wait()   # bloquea aquí si el evento fue cleared (pausado)

        success, result = rag.index_document(doc, progress_cb=on_progress)
        if success:
            ProjectDocument.objects.filter(pk=doc_id).update(
                index_status='done',
                chunk_count=result,
                index_progress=100,
                index_error='',
            )
        else:
            ProjectDocument.objects.filter(pk=doc_id).update(
                index_status='error',
                index_error=str(result)[:500],
                index_progress=0,
            )
    except Exception as exc:
        ProjectDocument.objects.filter(pk=doc_id).update(
            index_status='error',
            index_error=str(exc)[:500],
            index_progress=0,
        )
    finally:
        _pause_events.pop(doc_id, None)


def _trigger_indexing(doc: ProjectDocument) -> None:
    """Lanza la indexación en un thread daemon para no bloquear la respuesta HTTP."""
    event = threading.Event()
    event.set()   # estado inicial: corriendo
    _pause_events[doc.pk] = event
    t = threading.Thread(target=_index_worker, args=(doc.pk, event), daemon=True)
    t.start()


# ── Vistas ────────────────────────────────────────────────────────────────────

@login_required
def doc_list(request, project_pk):
    project   = get_object_or_404(Project, pk=project_pk, owner=request.user)
    documents = project.documents.all()
    return render(request, 'docs/list.html', {
        'project':   project,
        'documents': documents,
    })


@login_required
@require_POST
def doc_create(request, project_pk):
    project  = get_object_or_404(Project, pk=project_pk, owner=request.user)
    title    = request.POST.get('title', '').strip() or 'Sin título'
    doc_type = request.POST.get('doc_type', 'text')
    content  = request.POST.get('content', '').strip()
    file     = request.FILES.get('file')

    doc = ProjectDocument(project=project, title=title)

    if doc_type == 'pdf' and file:
        if not file.name.lower().endswith('.pdf'):
            return render(request, 'docs/list.html', {
                'project':   project,
                'documents': project.documents.all(),
                'error':     'Solo se permiten archivos PDF.',
                'open_tab':  'pdf',
            })
        doc.doc_type = 'pdf'
        doc.file = file
    else:
        doc.doc_type = 'text'
        doc.content  = content

    doc.save()
    _trigger_indexing(doc)   # ← indexación vectorial asíncrona
    return redirect('docs:list', project_pk=project_pk)


@login_required
@require_POST
def doc_delete(request, pk):
    doc = get_object_or_404(ProjectDocument, pk=pk, project__owner=request.user)
    project_pk = doc.project_id
    # Eliminar vectores del índice antes de borrar el registro
    rag.delete_document_vectors(project_pk, doc.pk)
    if doc.file:
        doc.file.delete(save=False)
    doc.delete()
    return redirect('docs:list', project_pk=project_pk)


@login_required
@require_POST
def doc_reindex(request, pk):
    """Re-indexa un documento manualmente (p.ej. si hubo error)."""
    doc = get_object_or_404(ProjectDocument, pk=pk, project__owner=request.user)
    _trigger_indexing(doc)
    return redirect('docs:list', project_pk=doc.project_id)


@login_required
def doc_index_status(request, pk):
    """Endpoint AJAX para consultar el estado de indexación de un documento."""
    doc = get_object_or_404(ProjectDocument, pk=pk, project__owner=request.user)
    return JsonResponse({
        'index_status':   doc.index_status,
        'chunk_count':    doc.chunk_count,
        'index_progress': doc.index_progress,
        'index_error':    doc.index_error,
    })


@login_required
@require_POST
def doc_pause(request, pk):
    """Pausa la indexación en curso de un documento."""
    doc = get_object_or_404(ProjectDocument, pk=pk, project__owner=request.user)
    if doc.index_status not in ('indexing', 'pending'):
        doc.refresh_from_db()
        return JsonResponse({
            'ok': False, 'reason': 'not indexing',
            'index_status':   doc.index_status,
            'index_progress': doc.index_progress,
            'chunk_count':    doc.chunk_count,
            'index_error':    doc.index_error,
        })
    event = _pause_events.get(doc.pk)
    if event:
        event.clear()   # bloquea el thread en el próximo on_progress
    # Forzar estado paused sin importar si el thread vive o no
    ProjectDocument.objects.filter(pk=pk).update(index_status='paused')
    doc.refresh_from_db()
    return JsonResponse({
        'ok': True,
        'index_status':   doc.index_status,
        'index_progress': doc.index_progress,
        'chunk_count':    doc.chunk_count,
        'index_error':    doc.index_error,
    })


@login_required
@require_POST
def doc_resume(request, pk):
    """Reanuda la indexación pausada de un documento."""
    doc = get_object_or_404(ProjectDocument, pk=pk, project__owner=request.user)
    if doc.index_status != 'paused':
        doc.refresh_from_db()
        return JsonResponse({
            'ok': False, 'reason': 'not paused',
            'index_status':   doc.index_status,
            'index_progress': doc.index_progress,
            'chunk_count':    doc.chunk_count,
            'index_error':    doc.index_error,
        })
    event = _pause_events.get(doc.pk)
    if event:
        # El thread sigue vivo: solo reanudar
        ProjectDocument.objects.filter(pk=pk).update(index_status='indexing')
        event.set()
    else:
        # El thread murió (reinicio del servidor): re-indexar desde cero
        _trigger_indexing(doc)
    doc.refresh_from_db()
    return JsonResponse({
        'ok': True,
        'index_status':   doc.index_status,
        'index_progress': doc.index_progress,
        'chunk_count':    doc.chunk_count,
        'index_error':    doc.index_error,
    })

