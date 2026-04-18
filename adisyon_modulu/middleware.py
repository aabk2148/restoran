import ipaddress
import logging
import uuid

from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import redirect
from django.urls import reverse

from .lisans import lisans


request_logger = logging.getLogger("app.request")


class RequestLogMiddleware:
    """Her istege bir request id ekler ve 500 hatalarini ayrintili loglar."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]

        try:
            response = self.get_response(request)
        except Exception:
            self._log_exception(request)
            raise

        if response.status_code >= 500:
            request_logger.error(
                "500 response returned",
                extra=self._build_extra(request, status_code=response.status_code),
            )

        response["X-Request-ID"] = request.request_id
        return response

    def _log_exception(self, request):
        request_logger.exception(
            "Unhandled application exception",
            extra=self._build_extra(request, status_code=500),
        )

    @staticmethod
    def _build_extra(request, status_code):
        user = getattr(request, "user", None)
        return {
            "request_id": getattr(request, "request_id", "-"),
            "method": request.method,
            "path": request.get_full_path(),
            "status_code": status_code,
            "remote_addr": RequestLogMiddleware._istemci_ip_al(request),
            "user_name": getattr(user, "get_username", lambda: "anon")() if getattr(user, "is_authenticated", False) else "anon",
        }

    @staticmethod
    def _istemci_ip_al(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return (request.META.get("REMOTE_ADDR") or "").strip()


class YerelAgErisimMiddleware:
    """Uygulamayi yalnizca localhost ve yerel ag istemcilerine acik tutar."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "LAN_ONLY_MODE", False):
            return self.get_response(request)

        istemci_ip = self._istemci_ip_al(request)
        if istemci_ip and self._izinli_ip_mi(istemci_ip):
            return self.get_response(request)

        return HttpResponseForbidden("Bu uygulama yalnizca yerel ag erisimi icin aciktir.")

    @staticmethod
    def _istemci_ip_al(request):
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return (request.META.get("REMOTE_ADDR") or "").strip()

    @staticmethod
    def _izinli_ip_mi(deger):
        try:
            ip = ipaddress.ip_address(deger)
        except ValueError:
            return False

        return ip.is_loopback or ip.is_private or ip.is_link_local


class LisansMiddleware:
    """Her istekte lisans kontrolu yapan middleware."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        muaf_urls = [
            reverse("lisans_aktivasyon"),
            reverse("admin:login"),
            "/admin/",
            "/static/",
            "/media/",
        ]

        if any(request.path.startswith(url) for url in muaf_urls if isinstance(url, str)):
            return self.get_response(request)

        if request.path in muaf_urls:
            return self.get_response(request)

        gecerli, mesaj, sonuc = lisans.lisans_kontrol()

        if not gecerli:
            messages.error(request, f"Lisans hatasi: {mesaj}")
            return redirect("lisans_aktivasyon")

        return self.get_response(request)
