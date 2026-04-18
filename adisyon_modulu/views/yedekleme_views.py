from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import redirect, render

from ..backup_manager import YedeklemeYoneticisi
from ..backup_service import aktif_yedekleme_ayari, yedek_olustur_ve_kaydet
from ..models import YedekKaydi
from .auth_views import yonetici_mi


def _ayar_formunu_kaydet(request, ayar):
    ayar.aktif = request.POST.get("aktif") == "on"
    ayar.yedekleme_tipi = request.POST.get("yedek_tipi", "yerel")
    ayar.zaman_araligi = int(request.POST.get("zaman_araligi", ayar.zaman_araligi or 1))
    ayar.yedekleme_saati = request.POST.get("yedekleme_saati", "03:00") or "03:00"
    ayar.yerel_klasor = request.POST.get("yerel_klasor", ayar.yerel_klasor).strip() or ayar.yerel_klasor
    ayar.max_yerel_yedek = max(1, int(request.POST.get("max_yerel_yedek", ayar.max_yerel_yedek or 10)))
    ayar.save()
    return ayar


def _yedek_sec(ayar, dosya_adi=None):
    yonetici = YedeklemeYoneticisi(ayar)
    yedekler = yonetici.mevcut_yedekleri_listele()
    if not yedekler:
        return None

    if not dosya_adi:
        return Path(yedekler[0]["yol"])

    hedef_klasor = Path(ayar.yerel_klasor).resolve()
    aday = (hedef_klasor / dosya_adi).resolve()
    if hedef_klasor not in aday.parents and aday != hedef_klasor / dosya_adi:
        return None
    if not aday.exists() or aday.suffix.lower() != ".zip":
        return None
    return aday


@login_required
@user_passes_test(yonetici_mi)
def yedekleme_sayfasi(request):
    ayar = aktif_yedekleme_ayari()
    yonetici = YedeklemeYoneticisi(ayar)

    context = {
        "ayar": ayar,
        "mevcut_yedekler": yonetici.mevcut_yedekleri_listele(),
        "son_yedekler": YedekKaydi.objects.order_by("-tarih")[:20],
        "yedek_kapsami": yonetici.yedek_kapsamini_ozetle(),
        "haftalik_tek_yedek": int(ayar.zaman_araligi or 1) >= 7,
    }
    return render(request, "adisyon_modulu/yedekleme.html", context)


@login_required
@user_passes_test(yonetici_mi)
def yedekleme_ayarlari_kaydet(request):
    if request.method == "POST":
        ayar = aktif_yedekleme_ayari()
        _ayar_formunu_kaydet(request, ayar)
        messages.success(request, "Yedekleme ayarlari kaydedildi.")
    return redirect("yedekleme_sayfasi")


@login_required
@user_passes_test(yonetici_mi)
def yedek_al_manuel(request):
    if request.method == "POST":
        ayar = aktif_yedekleme_ayari()
        _ayar_formunu_kaydet(request, ayar)
        sonuc = yedek_olustur_ve_kaydet(ayar, aciklama="Panelden manuel yedek")

        if sonuc["basarili"]:
            messages.success(request, f"Yedek basariyla alindi: {sonuc['dosya_adi']}")
        else:
            messages.error(request, f"Yedek alinamadi: {sonuc.get('hata', 'Bilinmeyen hata')}")

    return redirect("yedekleme_sayfasi")


@login_required
@user_passes_test(yonetici_mi)
def yedek_geri_yukle(request):
    if request.method == "POST":
        ayar = aktif_yedekleme_ayari()
        secilen = _yedek_sec(ayar, request.POST.get("geri_yukle_dosya"))
        if secilen is None:
            messages.error(request, "Geri yuklenecek uygun bir yedek bulunamadi.")
            return redirect("yedekleme_sayfasi")

        yonetici = YedeklemeYoneticisi(ayar)
        sonuc = yonetici.geri_yukle(secilen)

        if sonuc["basarili"]:
            YedekKaydi.objects.create(
                yedek_tipi=ayar.yedekleme_tipi,
                dosya_adi=secilen.name,
                durum="basari",
                aciklama="Otomatik geri yukleme tamamlandi",
            )
            messages.success(
                request,
                f"Geri yukleme tamamlandi: {secilen.name}. Devam etmeden uygulamayi yeniden baslatmaniz onerilir.",
            )
        else:
            YedekKaydi.objects.create(
                yedek_tipi=ayar.yedekleme_tipi,
                dosya_adi=secilen.name,
                durum="basarisiz",
                hata_mesaji=sonuc.get("hata", "Bilinmeyen hata"),
                aciklama="Otomatik geri yukleme basarisiz",
            )
            messages.error(request, f"Geri yukleme basarisiz: {sonuc.get('hata', 'Bilinmeyen hata')}")

    return redirect("yedekleme_sayfasi")
