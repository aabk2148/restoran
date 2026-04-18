from functools import wraps

from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import redirect


MODULE_DEFINITIONS = [
    {"id": "management-home", "label": "Yonetici Kontrol Paneli"},
    {"id": "kitchen-panel", "label": "Asci Paneli"},
    {"id": "waiter-panel", "label": "Garson Paneli"},
    {"id": "puantaj-panel", "label": "Personel Puantaj"},
    {"id": "reservation-panel", "label": "Rezervasyon"},
    {"id": "quick-sale", "label": "Hizli Satis"},
    {"id": "reports-panel", "label": "Raporlar"},
    {"id": "system-admin", "label": "Sistem"},
    {"id": "table-admin", "label": "Masalar"},
    {"id": "xml-transfer", "label": "XML Aktar"},
    {"id": "backup", "label": "Yedekleme"},
    {"id": "printer-management", "label": "Yazicilar"},
    {"id": "suppliers", "label": "Tedarikciler"},
    {"id": "loyalty", "label": "Sadakat"},
    {"id": "barcode-admin", "label": "Barkod"},
    {"id": "production", "label": "Uretim"},
    {"id": "products", "label": "Urunler"},
    {"id": "expense-entry", "label": "Gider"},
    {"id": "reservation-new", "label": "Rezervasyon Ekle"},
    {"id": "reservation-list", "label": "Rezervasyon Listesi"},
]


def module_choices():
    return [(module["id"], module["label"]) for module in MODULE_DEFINITIONS]


def default_enabled_module_ids():
    return [module["id"] for module in MODULE_DEFINITIONS]


def module_label(module_id):
    for module in MODULE_DEFINITIONS:
        if module["id"] == module_id:
            return module["label"]
    return module_id


def get_module_settings():
    from .models import ModulAyari

    settings_obj, _ = ModulAyari.objects.get_or_create(pk=1)
    return settings_obj


def enabled_module_ids():
    settings_obj = get_module_settings()
    aktif_moduller = settings_obj.aktif_moduller
    if aktif_moduller is None:
        return set(default_enabled_module_ids())
    return set(aktif_moduller)


def is_module_enabled(module_id):
    return module_id in enabled_module_ids()


def module_required(module_id, redirect_name="ana_sayfa"):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            if is_module_enabled(module_id):
                return view_func(request, *args, **kwargs)
            if "/api/" in request.path or request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {
                        "success": False,
                        "error": f"{module_label(module_id)} modulu su anda kullanima kapali.",
                    },
                    status=403,
                )
            messages.error(
                request,
                f"{module_label(module_id)} modulu su anda kullanima kapali.",
            )
            return redirect(redirect_name)

        return wrapped

    return decorator
