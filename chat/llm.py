"""
Servicio LLM: carga modelos GGUF con llama-cpp-python y genera respuestas.
"""
import threading
import atexit

_lock   = threading.Lock()
_models = {}   # { model_path: Llama }


def _cleanup():
    """Libera todos los modelos al apagar el proceso (evita crash de Metal)."""
    with _lock:
        for llm in list(_models.values()):
            try:
                llm.close()
            except Exception:
                pass
        _models.clear()


atexit.register(_cleanup)


def _load(model_path: str):
    try:
        from llama_cpp import Llama
    except ImportError:
        raise RuntimeError(
            "llama-cpp-python no instalado. "
            "Ejecuta: CMAKE_ARGS='-DLLAMA_METAL=on' pip install llama-cpp-python"
        )

    with _lock:
        if model_path not in _models:
            _models[model_path] = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_gpu_layers=-1,   # Metal en Apple Silicon; 0 = solo CPU
                verbose=False,
            )
    return _models[model_path]


def generate(model_path: str, messages: list, max_tokens: int = 512, temperature: float = 0.7) -> str:
    """
    messages: lista de dicts [{role: 'user'|'assistant'|'system', content: str}]
    Devuelve el texto generado por el modelo.
    """
    llm = _load(model_path)
    result = llm.create_chat_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["<|im_end|>", "<|eot_id|>", "<|end|>"],
    )
    return result["choices"][0]["message"]["content"].strip()


# ─────────────────────────────────────────────────────────────────────────────
# OpenAI API
# ─────────────────────────────────────────────────────────────────────────────

def generate_openai(
    api_key: str,
    model_name: str,
    messages: list,
    max_tokens: int = 1024,
    temperature: float = 0.7,
) -> str:
    """
    Llama a la API de OpenAI con el mismo formato de mensajes.
    Lanza una excepción con el mensaje de error si falla.
    """
    import requests as _req

    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type':  'application/json',
    }
    payload = {
        'model':       model_name,
        'messages':    messages,
        'max_tokens':  max_tokens,
        'temperature': temperature,
    }
    resp = _req.post(
        'https://api.openai.com/v1/chat/completions',
        headers=headers,
        json=payload,
        timeout=60,
    )
    if not resp.ok:
        try:
            err = resp.json().get('error', {}).get('message', resp.text)
        except Exception:
            err = resp.text
        raise RuntimeError(f'OpenAI error {resp.status_code}: {err}')
    return resp.json()['choices'][0]['message']['content'].strip()

