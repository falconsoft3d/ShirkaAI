import os
import threading
from django.apps import AppConfig


class DocsConfig(AppConfig):
    name = 'docs'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        # Solo correr en el proceso principal (no en el monitor del StatReloader)
        if os.environ.get('RUN_MAIN') != 'true':
            return
        # Diferir el acceso a BD hasta que Django esté completamente listo
        t = threading.Thread(target=self._reset_stuck_docs, daemon=True)
        t.start()

    @staticmethod
    def _reset_stuck_docs():
        import time
        time.sleep(0.5)  # esperar a que Django termine de inicializarse
        try:
            from .models import ProjectDocument
            count = ProjectDocument.objects.filter(index_status='indexing').update(
                index_status='pending', index_progress=0
            )
            if count:
                import logging
                logging.getLogger(__name__).info(
                    '%d doc(s) atascados en "indexing" reseteados a "pending".', count
                )
        except Exception:
            pass
