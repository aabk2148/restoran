from .base import *
import os
import socket
import ipaddress


def _ozel_ag_ip_mi(deger):
    try:
        ip = ipaddress.ip_address(deger)
    except ValueError:
        return False

    return ip.is_loopback or ip.is_private or ip.is_link_local


def _yerel_hostlari_topla():
    hostlar = {"127.0.0.1", "localhost", "192.168.1.200"}

    try:
        hostlar.add(socket.gethostname())
        hostlar.add(socket.getfqdn())
    except Exception:
        pass

    try:
        for bilgi in socket.getaddrinfo(socket.gethostname(), None, family=socket.AF_INET):
            ip = bilgi[4][0]
            if ip and _ozel_ag_ip_mi(ip):
                hostlar.add(ip)
    except Exception:
        pass

    ekstra = os.getenv("EXTRA_ALLOWED_HOSTS", "")
    for host in ekstra.split(","):
        host = host.strip()
        if host:
            hostlar.add(host)

    return sorted(hostlar)


def _csrf_originleri_uret(hostlar):
    originler = set()
    for host in hostlar:
        if host == "*":
            continue
        originler.add(f"http://{host}:8000")

    ekstra = os.getenv("EXTRA_CSRF_TRUSTED_ORIGINS", "")
    for origin in ekstra.split(","):
        origin = origin.strip()
        if origin:
            originler.add(origin)

    return sorted(originler)


DEBUG = False

LAN_ONLY_MODE = os.getenv("LAN_ONLY_MODE", "True").lower() in {"1", "true", "yes", "on"}

ALLOWED_HOSTS = _yerel_hostlari_topla()

CSRF_TRUSTED_ORIGINS = _csrf_originleri_uret(ALLOWED_HOSTS)

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "SAMEORIGIN"

STATIC_ROOT = BASE_DIR / "staticfiles"

DB_NAME = os.getenv("DB_NAME", "restoran_db")
DB_USER = os.getenv("DB_USER", "restoran_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "123456")
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = os.getenv("DB_PORT", "5432")

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": DB_NAME,
        "USER": DB_USER,
        "PASSWORD": DB_PASSWORD,
        "HOST": DB_HOST,
        "PORT": DB_PORT,
        "CONN_MAX_AGE": 60,
    }
}
