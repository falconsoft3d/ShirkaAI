from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from .models import Task, Execution
from projects.models import Project


@login_required
def task_list(request):
    tasks = Task.objects.filter(owner=request.user).select_related('project')
    projects = Project.objects.filter(owner=request.user)
    return render(request, 'tasks/list.html', {
        'tasks': tasks,
        'projects': projects,
    })


@login_required
def task_new(request):
    projects = Project.objects.filter(owner=request.user)
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        active      = request.POST.get('active') == 'on'
        project_id  = request.POST.get('project') or None

        if not title:
            return render(request, 'tasks/form.html', {
                'projects': projects,
                'error': 'El título es obligatorio.',
                'form_data': request.POST,
            })

        project = None
        if project_id:
            project = get_object_or_404(Project, pk=project_id, owner=request.user)

        Task.objects.create(
            title=title,
            description=description,
            active=active,
            project=project,
            owner=request.user,
        )
        return redirect('tasks:list')

    return render(request, 'tasks/form.html', {'projects': projects})


@login_required
def task_edit(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    projects = Project.objects.filter(owner=request.user)

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        active      = request.POST.get('active') == 'on'
        project_id  = request.POST.get('project') or None

        if not title:
            return render(request, 'tasks/form.html', {
                'task': task,
                'projects': projects,
                'error': 'El título es obligatorio.',
                'form_data': request.POST,
            })

        project = None
        if project_id:
            project = get_object_or_404(Project, pk=project_id, owner=request.user)

        task.title       = title
        task.description = description
        task.active      = active
        task.project     = project
        task.save()
        return redirect('tasks:list')

    return render(request, 'tasks/form.html', {'task': task, 'projects': projects})


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.active = not task.active
    task.save(update_fields=['active'])
    return redirect('tasks:list')


@login_required
@require_POST
def task_delete(request, pk):
    task = get_object_or_404(Task, pk=pk, owner=request.user)
    task.delete()
    return redirect('tasks:list')


# ── EXECUTIONS ────────────────────────────────────────────────────────────────

@login_required
def execution_list(request):
    executions = Execution.objects.filter(owner=request.user).select_related('task')
    return render(request, 'tasks/executions_list.html', {'executions': executions})


@login_required
def execution_new(request):
    tasks = Task.objects.filter(owner=request.user)
    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        task_id     = request.POST.get('task') or None

        if not title:
            return render(request, 'tasks/executions_form.html', {
                'tasks': tasks,
                'error': 'El título es obligatorio.',
                'form_data': request.POST,
            })

        source_task = None
        if task_id:
            source_task = get_object_or_404(Task, pk=task_id, owner=request.user)

        Execution.objects.create(
            title=title,
            description=description,
            task=source_task,
            owner=request.user,
        )
        return redirect('tasks:execution_list')

    return render(request, 'tasks/executions_form.html', {'tasks': tasks})


@login_required
def execution_edit(request, pk):
    execution = get_object_or_404(Execution, pk=pk, owner=request.user)
    tasks = Task.objects.filter(owner=request.user)

    if request.method == 'POST':
        title       = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        task_id     = request.POST.get('task') or None

        if not title:
            return render(request, 'tasks/executions_form.html', {
                'execution': execution,
                'tasks': tasks,
                'error': 'El título es obligatorio.',
                'form_data': request.POST,
            })

        source_task = None
        if task_id:
            source_task = get_object_or_404(Task, pk=task_id, owner=request.user)

        execution.title       = title
        execution.description = description
        execution.task        = source_task
        execution.save()
        return redirect('tasks:execution_list')

    return render(request, 'tasks/executions_form.html', {
        'execution': execution,
        'tasks': tasks,
    })


@login_required
@require_POST
def execution_delete(request, pk):
    execution = get_object_or_404(Execution, pk=pk, owner=request.user)
    execution.delete()
    return redirect('tasks:execution_list')
