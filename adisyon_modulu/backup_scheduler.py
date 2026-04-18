import logging
import os
import sys
import threading
import time

from django.db.utils import OperationalError, ProgrammingError

from .backup_service import otomatik_yedekleri_calistir

logger = logging.getLogger(__name__)
_scheduler_started = False


def start_backup_scheduler():
    global _scheduler_started

    if _scheduler_started or not _should_start_scheduler():
        return

    _scheduler_started = True
    thread = threading.Thread(target=_backup_loop, name="elaki-backup-scheduler", daemon=True)
    thread.start()


def _should_start_scheduler():
    argv = " ".join(sys.argv).lower()
    engellenen = ("makemigrations", "migrate", "collectstatic", "shell", "test", "yedek_al", "yedek_geri_yukle")
    if any(komut in argv for komut in engellenen):
        return False

    if "runserver" in argv:
        return os.environ.get("RUN_MAIN") == "true"

    return False


def _backup_loop():
    while True:
        try:
            otomatik_yedekleri_calistir()
        except (OperationalError, ProgrammingError):
            pass
        except Exception:
            logger.exception("Yedek zamanlayicisi beklenmeyen bir hata ile karsilasti.")
        time.sleep(60)
