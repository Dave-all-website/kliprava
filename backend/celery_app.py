from celery import Celery
from config import settings

# Patch otomatis untuk kompatibilitas penuh dengan Redis Windows (RESP2 protocol & bypass 'HELLO' command)
try:
    import redis.connection
    redis.connection.MaintNotificationsAbstractConnection._configure_maintenance_notifications = lambda self, *a, **k: None
    _orig_conn_init = redis.connection.Connection.__init__
    def _patched_conn_init(self, *args, **kwargs):
        kwargs["protocol"] = 2
        _orig_conn_init(self, *args, **kwargs)
    redis.connection.Connection.__init__ = _patched_conn_init
except Exception:
    pass

celery_app = Celery(
    "media_converter",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=900,         # Hard limit 15 menit per task
    task_soft_time_limit=840,    # Soft limit 14 menit
    worker_prefetch_multiplier=1, # Mencegah 1 worker mengambil banyak task berat sekaligus
    result_expires=86400,        # Hasil task di Redis disimpan selama 24 jam
    broker_transport_options={"protocol": 2},
    result_backend_transport_options={"protocol": 2},
)
