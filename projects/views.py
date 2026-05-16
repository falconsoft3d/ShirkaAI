from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Project
from llm_models.models import LLMModel


def _available_models():
    return LLMModel.objects.filter(status__in=['ready', 'active'])


@login_required
def project_new(request):
    return render(request, 'projects/form.html', {
        'available_models': _available_models(),
    })


@login_required
def project_list(request):
    projects = list(Project.objects.filter(owner=request.user).select_related('model'))

    try:
        from docs.embeddings import get_vector_stats
        for p in projects:
            p.vector_stats = get_vector_stats(p.pk)
    except Exception:
        for p in projects:
            p.vector_stats = {'docs': 0, 'memory': 0}

    return render(request, 'projects/list.html', {
        'projects': projects,
        'available_models': _available_models(),
    })


@login_required
@require_POST
def project_create(request):
    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    model_id = request.POST.get('model_id') or None
    llm = None
    if model_id:
        llm = LLMModel.objects.filter(pk=model_id, status__in=['ready', 'active']).first()
    if not name:
        return render(request, 'projects/form.html', {
            'available_models': _available_models(),
            'error': 'El nombre es obligatorio.',
            'form_name': name,
            'form_description': description,
            'form_model_id': model_id,
        })
    Project.objects.create(name=name, description=description, model=llm, owner=request.user)
    return redirect('projects:list')


@login_required
@require_POST
def project_set_model(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    model_id = request.POST.get('model_id') or None
    llm = None
    if model_id:
        llm = LLMModel.objects.filter(pk=model_id, status__in=['ready', 'active']).first()
    project.model = llm
    project.save(update_fields=['model', 'updated_at'])
    return redirect('projects:list')


@login_required
@require_POST
def project_set_api(request, pk):
    """Configura el proveedor de IA (local o OpenAI) de un proyecto."""
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    provider = request.POST.get('api_provider', 'local')
    if provider not in ('local', 'openai'):
        provider = 'local'
    project.api_provider = provider
    if provider == 'openai':
        new_key = request.POST.get('api_key', '').strip()
        # Preserve existing key if the masked placeholder was submitted
        if new_key and new_key != project.api_key_masked:
            project.api_key = new_key
        project.api_model_name = request.POST.get('api_model_name', 'gpt-4o-mini').strip()
        project.model = None  # no se usa modelo local en modo OpenAI
    else:
        model_id = request.POST.get('model_id') or None
        llm = None
        if model_id:
            llm = LLMModel.objects.filter(pk=model_id, status__in=['ready', 'active']).first()
        project.model = llm
        project.api_key = ''
        project.api_model_name = ''
    project.save(update_fields=['api_provider', 'api_key', 'api_model_name', 'model', 'updated_at'])
    return redirect('projects:list')


@login_required
@require_POST
def project_delete(request, pk):
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    project.delete()
    return redirect('projects:list')


@login_required
@require_POST
def project_clear_memory(request, pk):
    """Elimina todos los vectores de memoria del chat de un proyecto."""
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    try:
        from docs.embeddings import _get_client
        client = _get_client()
        client.delete_collection(f'memory_{project.pk}')
    except Exception:
        pass
    return redirect('projects:memory', pk=pk)


@login_required
def project_memory(request, pk):
    """Lista todas las entradas de memoria vectorial del chat de un proyecto."""
    project = get_object_or_404(Project, pk=pk, owner=request.user)
    from docs.embeddings import get_all_memories
    memories = get_all_memories(project.pk)
    return render(request, 'projects/memory.html', {
        'project': project,
        'memories': memories,
    })

