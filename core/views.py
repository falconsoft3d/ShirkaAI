from django.shortcuts import render
from django.contrib.auth.decorators import login_required


def home(request):
    features = [
        {'icon': '🧠', 'title': 'Modelos LLM', 'desc': 'Llama, Mistral, Qwen, DeepSeek y más corriendo localmente.'},
        {'icon': '🔌', 'title': 'Integraciones', 'desc': 'Conecta Odoo, WhatsApp, Gmail, calendarios y ERPs.'},
        {'icon': '💾', 'title': 'Memoria', 'desc': 'Historial, contactos, documentos y preferencias persistentes.'},
        {'icon': '🔒', 'title': 'Privacidad', 'desc': 'Tus datos en tu servidor, sin dependencias de terceros.'},
    ]
    return render(request, 'core/home.html', {'features': features})


@login_required
def dashboard(request):
    setup_steps = [
        {'number': '1', 'color': 'bg-brand-700/30 text-brand-400',
         'title': 'Agrega tu primer modelo LLM',
         'desc': 'Conecta Llama, Mistral u otro modelo open-source vía Ollama o API.'},
        {'number': '2', 'color': 'bg-green-700/30 text-green-400',
         'title': 'Configura tus integraciones',
         'desc': 'Conecta Gmail, WhatsApp, Odoo u otras apps para centralizar tu información.'},
        {'number': '3', 'color': 'bg-purple-700/30 text-purple-400',
         'title': 'Sube documentos y crea contexto',
         'desc': 'Agrega PDFs, notas y datos para que la IA tenga memoria de tu negocio.'},
        {'number': '4', 'color': 'bg-yellow-700/30 text-yellow-400',
         'title': 'Automatiza tareas',
         'desc': 'Crea flujos para resumir, responder, generar reportes o crear tickets automáticamente.'},
    ]
    return render(request, 'core/dashboard.html', {'setup_steps': setup_steps})
