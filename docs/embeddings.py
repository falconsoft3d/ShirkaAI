"""
docs/embeddings.py
──────────────────
Motor RAG (Retrieval-Augmented Generation) para ShirkaAI.

• Usa ChromaDB como vector store persistente (chroma_db/ en la raíz del proyecto).
• Usa sentence-transformers `all-MiniLM-L6-v2` para embeddings locales (≈80 MB, solo CPU).
• Cada proyecto tiene su propia colección: project_{pk}.
• Flujo: subir doc → chunking → embedding → ChromaDB
         chat     → embed query → búsqueda coseno → top-K chunks → contexto del LLM
"""

import gc
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ── Directorio persistente para ChromaDB ──────────────────────────────────────
CHROMA_DIR = Path(__file__).resolve().parent.parent / 'chroma_db'
CHROMA_DIR.mkdir(exist_ok=True)

# Parámetros de chunking
CHUNK_SIZE  = 800   # caracteres por fragmento
CHUNK_OVER  = 150   # solapamiento entre fragmentos
BATCH_SIZE  = 64    # fragmentos por llamada a ChromaDB


# ── Clientes (lazy, singleton por proceso) ────────────────────────────────────
_chroma_client = None
_embed_fn       = None


def _get_client():
    global _chroma_client
    if _chroma_client is None:
        import chromadb
        _chroma_client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return _chroma_client


def _get_ef():
    """Función de embedding ONNX via DefaultEmbeddingFunction (sin PyTorch)."""
    global _embed_fn
    if _embed_fn is None:
        from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
        _embed_fn = DefaultEmbeddingFunction()
    return _embed_fn


def _warmup():
    """Pre-carga el modelo ONNX en background al iniciar el servidor."""
    import threading
    def _load():
        try:
            _get_ef()
            logger.info('Modelo de embeddings ONNX pre-cargado correctamente.')
        except Exception as exc:
            logger.warning('No se pudo pre-cargar el modelo de embeddings: %s', exc)
    t = threading.Thread(target=_load, daemon=True)
    t.start()

_warmup()


def _get_collection(project_pk):
    """Obtiene o crea la colección vectorial de un proyecto."""
    client = _get_client()
    return client.get_or_create_collection(
        name=f'project_{project_pk}',
        embedding_function=_get_ef(),
        metadata={'hnsw:space': 'cosine'},
    )


# ── Chunking ──────────────────────────────────────────────────────────────────

def _chunk_text(text: str) -> list[str]:
    """
    Divide el texto en fragmentos solapados.
    Intenta cortar en límites de párrafo/oración para mejor calidad semántica.
    """
    # Normalizar líneas en blanco excesivas
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    if not text:
        return []

    chunks = []
    start  = 0
    length = len(text)

    while start < length:
        end = min(start + CHUNK_SIZE, length)

        if end < length:
            # Preferir corte en doble newline (párrafo)
            cut = text.rfind('\n\n', start, end)
            if cut <= start + CHUNK_SIZE // 3:
                # Si no hay, cortar en punto o espacio
                cut = text.rfind('. ', start, end)
            if cut <= start + CHUNK_SIZE // 3:
                cut = text.rfind(' ', start, end)
            if cut > start + CHUNK_SIZE // 3:
                end = cut + 1  # incluir el espacio/newline

        chunk = text[start:end].strip()
        if len(chunk) > 50:  # descartar fragmentos muy cortos
            chunks.append(chunk)

        start = end - CHUNK_OVER
        if start >= length:
            break

    return chunks


# ── Extracción de texto ────────────────────────────────────────────────────────

def extract_text(doc) -> str:
    """
    Extrae el texto plano de un ProjectDocument.
    Para PDF usa pypdf. Para texto devuelve doc.content.
    """
    if doc.doc_type == 'pdf' and doc.file:
        try:
            from pypdf import PdfReader
            reader = PdfReader(doc.file.path)
            pages = [p.extract_text() or '' for p in reader.pages]
            return '\n\n'.join(p for p in pages if p.strip())
        except Exception as exc:
            raise RuntimeError(f'Error extrayendo PDF: {exc}') from exc
    return doc.content or ''


# ── Indexación ────────────────────────────────────────────────────────────────

def index_document(doc, progress_cb=None) -> tuple[bool, str | int]:
    """
    Indexa un ProjectDocument en ChromaDB.

    Args:
        progress_cb: callable opcional que recibe (pct: int, processed: int, total: int)

    Returns:
        (True,  num_chunks)  si fue exitoso
        (False, mensaje_error) si falló
    """
    try:
        text = extract_text(doc)
    except RuntimeError as exc:
        return False, str(exc)

    if not text.strip():
        return False, 'El documento no tiene contenido de texto para indexar.'

    chunks = _chunk_text(text)
    if not chunks:
        return False, 'No se pudo generar ningún fragmento del documento.'

    total_chunks = len(chunks)

    try:
        collection = _get_collection(doc.project_id)

        # Eliminar versión anterior de este documento si existía
        try:
            collection.delete(where={'doc_id': str(doc.pk)})
        except Exception:
            pass

        # Insertar en lotes y reportar progreso
        processed = 0
        for i in range(0, total_chunks, BATCH_SIZE):
            batch      = chunks[i:i + BATCH_SIZE]
            batch_ids  = [f'doc_{doc.pk}_chunk_{i + j}' for j in range(len(batch))]
            batch_meta = [
                {'doc_id': str(doc.pk), 'doc_title': doc.title, 'chunk_idx': i + j}
                for j in range(len(batch))
            ]
            collection.add(ids=batch_ids, documents=batch, metadatas=batch_meta)
            processed += len(batch)
            if progress_cb:
                pct = int(processed / total_chunks * 100)
                progress_cb(pct, processed, total_chunks)

        gc.collect()
        logger.info('Indexado doc %s → %d fragmentos', doc.pk, processed)
        return True, processed

    except Exception as exc:
        logger.exception('Error indexando doc %s', doc.pk)
        return False, str(exc)


def delete_document_vectors(project_pk: int, doc_pk: int) -> None:
    """Elimina todos los vectores de un documento del índice del proyecto."""
    try:
        collection = _get_collection(project_pk)
        collection.delete(where={'doc_id': str(doc_pk)})
        logger.info('Vectores eliminados para doc %s del proyecto %s', doc_pk, project_pk)
    except Exception:
        pass  # No fallar si el doc nunca fue indexado


def delete_project_collection(project_pk: int) -> None:
    """Elimina la colección completa de un proyecto (útil al borrar el proyecto)."""
    try:
        client = _get_client()
        client.delete_collection(name=f'project_{project_pk}')
    except Exception:
        pass


def get_vector_stats(project_pk: int) -> dict:
    """
    Devuelve el conteo de vectores de documentos y de memoria para un proyecto.

    Returns:
        {'docs': int, 'memory': int}
    """
    stats = {'docs': 0, 'memory': 0}
    try:
        client = _get_client()
        existing = {c.name for c in client.list_collections()}
        if f'project_{project_pk}' in existing:
            stats['docs'] = _get_collection(project_pk).count()
        if f'memory_{project_pk}' in existing:
            stats['memory'] = _get_memory_collection(project_pk).count()
    except Exception:
        pass
    return stats


def get_all_memories(project_pk: int) -> list[dict]:
    """
    Devuelve todas las entradas de memoria del chat de un proyecto ordenadas
    por session y mensaje.

    Returns:
        Lista de dicts: {
            'id', 'session_pk', 'msg_pk',
            'user_msg', 'assistant_reply', 'source'
        }
    """
    try:
        client = _get_client()
        existing = {c.name for c in client.list_collections()}
        if f'memory_{project_pk}' not in existing:
            return []
        collection = _get_memory_collection(project_pk)
        total = collection.count()
        if total == 0:
            return []
        result = collection.get(
            include=['metadatas'],
            limit=total,
        )
        entries = []
        for chroma_id, meta in zip(result['ids'], result['metadatas']):
            entries.append({
                'id':              chroma_id,
                'session_pk':      meta.get('session_pk', ''),
                'msg_pk':          meta.get('msg_pk', ''),
                'user_msg':        meta.get('user_msg', ''),
                'assistant_reply': meta.get('assistant_reply', ''),
            })
        # Ordenar por session_pk y luego msg_pk numérico
        entries.sort(key=lambda e: (e['session_pk'], int(e['msg_pk']) if e['msg_pk'].isdigit() else 0))
        return entries
    except Exception:
        logger.exception('Error listando memorias del proyecto %s', project_pk)
        return []


# ── Memoria de chat ───────────────────────────────────────────────────────────

def _get_memory_collection(project_pk):
    """Obtiene o crea la colección de memoria de chat de un proyecto."""
    client = _get_client()
    return client.get_or_create_collection(
        name=f'memory_{project_pk}',
        embedding_function=_get_ef(),
        metadata={'hnsw:space': 'cosine'},
    )


def store_memory(project_pk: int, session_pk: int, msg_pk: int,
                 user_msg: str, assistant_reply: str) -> None:
    """
    Vectoriza y almacena un intercambio (usuario + asistente) como memoria del proyecto.
    Solo se embute el mensaje del usuario para que la búsqueda semántica funcione bien;
    la respuesta del asistente viaja como metadata.
    Se llama en un thread daemon para no bloquear la respuesta HTTP.
    """
    try:
        collection = _get_memory_collection(project_pk)
        # Embebemos SOLO el mensaje del usuario → el retrieval semántico coincide
        # con nuevas preguntas sobre el mismo tema.
        collection.add(
            ids=[f'mem_{session_pk}_{msg_pk}'],
            documents=[user_msg],          # ← solo la pregunta del usuario
            metadatas=[{
                'session_pk':       str(session_pk),
                'msg_pk':           str(msg_pk),
                'user_msg':         user_msg[:500],
                'assistant_reply':  assistant_reply[:2000],
                'source':           'memory',
            }],
        )
        logger.debug('Memoria almacenada: sesión %s mensaje %s', session_pk, msg_pk)
    except Exception:
        logger.exception('Error almacenando memoria del proyecto %s', project_pk)


def retrieve_memory(project_pk: int, query: str, n_results: int = 3) -> list[dict]:
    """
    Recupera intercambios anteriores del chat relevantes para la consulta actual.

    Returns:
        Lista de dicts: {'text': str, 'distance': float}
        Lista vacía si no hay memoria o se produce un error.
    """
    try:
        collection = _get_memory_collection(project_pk)
        total = collection.count()
        if total == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, total),
            include=['documents', 'metadatas', 'distances'],
        )

        memories = []
        for _doc, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0],
        ):
            # Umbral generoso (1.0) para no perder recuerdos relevantes.
            # Cosine distance en ChromaDB: 0 = idéntico, 1 = ortogonal, 2 = opuesto.
            if dist < 1.0:
                memories.append({
                    'text': (
                        f'Usuario: {meta["user_msg"]}\n'
                        f'Asistente: {meta["assistant_reply"]}'
                    ),
                    'distance': round(dist, 4),
                })

        return memories

    except Exception:
        logger.exception('Error recuperando memoria del proyecto %s', project_pk)
        return []


# ── Recuperación ──────────────────────────────────────────────────────────────

def retrieve_context(project_pk: int, query: str, n_results: int = 5) -> list[dict]:
    """
    Busca los fragmentos más relevantes para una consulta en la documentación del proyecto.

    Returns:
        Lista de dicts: {'text': str, 'title': str, 'distance': float}
        Lista vacía si no hay documentos indexados o se produce un error.
    """
    try:
        collection = _get_collection(project_pk)
        total = collection.count()
        if total == 0:
            return []

        results = collection.query(
            query_texts=[query],
            n_results=min(n_results, total),
            include=['documents', 'metadatas', 'distances'],
        )

        chunks = []
        for text, meta, dist in zip(
            results['documents'][0],
            results['metadatas'][0],
            results['distances'][0],
        ):
            # Distancia coseno en ChromaDB: 0 = idéntico, 2 = opuesto
            # Filtramos fragmentos poco relevantes (dist > 0.9)
            if dist < 0.9:
                chunks.append({
                    'text':     text,
                    'title':    meta.get('doc_title', 'Documento'),
                    'distance': round(dist, 4),
                })

        return chunks

    except Exception:
        logger.exception('Error recuperando contexto para proyecto %s', project_pk)
        return []
