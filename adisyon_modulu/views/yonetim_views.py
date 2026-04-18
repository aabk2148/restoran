from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, F, Max, Q
from django.urls import reverse
from django.shortcuts import render
from django.utils import timezone

from .auth_views import yonetici_mi
from ..dashboard import build_dashboard_context
from ..models import (
    Adisyon,
    Bolge,
    GarsonCagri,
    HizliSatis,
    HizliSatisUrun,
    KullaniciProfili,
    Masa,
    MenuSiparisTalebi,
    PersonelPuantaj,
    Rezervasyon,
    SiparisItem,
    Sube,
    StokKalemi,
)


ZERO = Decimal("0.00")


def _format_currency(value):
    value = Decimal(value or 0).quantize(Decimal("0.01"))
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _format_percent(value):
    return f"{value:+.1f}%"


def _minutes_since(dt, now=None):
    if not dt:
        return None
    now = now or timezone.now()
    return max(int((now - dt).total_seconds() // 60), 0)


def _duration_label(minutes):
    if minutes is None:
        return "-"
    if minutes < 60:
        return f"{minutes} dk"
    saat, dakika = divmod(minutes, 60)
    if dakika == 0:
        return f"{saat} sa"
    return f"{saat} sa {dakika} dk"


def _delta_percent(current, previous):
    current = Decimal(current or 0)
    previous = Decimal(previous or 0)
    if previous <= 0:
        return 100.0 if current > 0 else 0.0
    return float(((current - previous) / previous) * Decimal("100"))


def _sube_scope(user):
    if user.is_superuser:
        return list(Sube.objects.all().order_by("ad"))
    profil = getattr(user, "profil", None)
    if profil and profil.sube:
        return [profil.sube]
    return list(Sube.objects.all().order_by("ad"))


def _adisyon_total(adisyon):
    toplam = ZERO
    for item in adisyon.siparisler.all():
        if item.iptal_edildi or item.ikram_mi:
            continue
        toplam += Decimal(item.toplam_fiyat() or 0)
    toplam -= Decimal(adisyon.indirim_tutari or 0)
    return toplam if toplam > 0 else ZERO


def _rol_etiketi(user):
    if user.is_superuser:
        return "Yonetici"
    profil = getattr(user, "profil", None)
    return getattr(profil, "rol", "-")


def _build_manager_dashboard_context(user):
    now = timezone.now()
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)
    subeler = _sube_scope(user)
    sube_ids = [sube.id for sube in subeler]

    dashboard_links = build_dashboard_context(user)

    adisyon_today = list(
        Adisyon.objects.filter(sube_id__in=sube_ids, durum="Kapali", acilis_zamani__date=today)
        .select_related("sube", "masa")
        .prefetch_related("siparisler__urun")
    )
    adisyon_yesterday = list(
        Adisyon.objects.filter(sube_id__in=sube_ids, durum="Kapali", acilis_zamani__date=yesterday)
        .select_related("sube", "masa")
        .prefetch_related("siparisler__urun")
    )

    quick_sales_today = HizliSatis.objects.filter(sube_id__in=sube_ids, tarih__date=today).select_related("sube", "kullanici")
    quick_sales_yesterday = HizliSatis.objects.filter(sube_id__in=sube_ids, tarih__date=yesterday)

    ciro_today = sum((_adisyon_total(a) for a in adisyon_today), ZERO) + sum((s.toplam_tutar for s in quick_sales_today), ZERO)
    ciro_yesterday = sum((_adisyon_total(a) for a in adisyon_yesterday), ZERO) + sum((s.toplam_tutar for s in quick_sales_yesterday), ZERO)
    ciro_delta = _delta_percent(ciro_today, ciro_yesterday)

    hesap_sayisi_today = len(adisyon_today) + quick_sales_today.count()
    ortalama_sepet = (ciro_today / hesap_sayisi_today) if hesap_sayisi_today else ZERO

    aktif_masa_sayisi = Masa.objects.filter(sube_id__in=sube_ids, dolu_mu=True).count()
    toplam_masa_sayisi = Masa.objects.filter(sube_id__in=sube_ids).count()
    doluluk_orani = int((aktif_masa_sayisi / toplam_masa_sayisi) * 100) if toplam_masa_sayisi else 0

    aktif_personel = list(
        PersonelPuantaj.objects.filter(
            tarih=today,
            cikis_saati__isnull=True,
        )
        .filter(Q(sube_id__in=sube_ids) | Q(sube__isnull=True, user__profil__sube_id__in=sube_ids))
        .select_related("user", "sube", "user__profil")
        .order_by("giris_saati")
    )

    aktif_personel_ids = {kayit.user_id for kayit in aktif_personel}
    if user.is_authenticated and user.id not in aktif_personel_ids:
        aktif_personel.insert(0, type("AnlikPuantaj", (), {
            "user": user,
            "user_id": user.id,
            "sube": getattr(getattr(user, "profil", None), "sube", None),
            "toplam_sure_dakika": 0,
        })())

    aktif_personel_sayisi = len(aktif_personel)
    toplam_aktif_personel = KullaniciProfili.objects.filter(aktif=True, sube_id__in=sube_ids).count()

    bekleyen_mutfak_qs = (
        SiparisItem.objects.filter(
            adisyon__sube_id__in=sube_ids,
            adisyon__durum="Acik",
            hazir_mi=False,
            iptal_edildi=False,
        )
        .select_related("urun", "adisyon__masa", "adisyon__sube", "siparisi_alan")
        .order_by("eklenme_zamani")
    )
    bekleyen_mutfak_siparisleri = list(bekleyen_mutfak_qs[:8])
    bekleyen_mutfak_sayisi = bekleyen_mutfak_qs.count()
    en_eski_mutfak_siparisi = bekleyen_mutfak_siparisleri[0] if bekleyen_mutfak_siparisleri else None
    mutfak_bekleme_dakika = _minutes_since(getattr(en_eski_mutfak_siparisi, "eklenme_zamani", None), now)

    son_hazir_siparis = (
        SiparisItem.objects.filter(adisyon__sube_id__in=sube_ids, hazir_olma_zamani__isnull=False)
        .order_by("-hazir_olma_zamani")
        .first()
    )
    mutfak_bosta_dakika = _minutes_since(getattr(son_hazir_siparis, "hazir_olma_zamani", None), now)

    bekleyen_garson_cagrilari = list(
        GarsonCagri.objects.filter(sube_id__in=sube_ids, tamamlandi_mi=False)
        .select_related("sube")
        .order_by("zaman")[:8]
    )
    bekleyen_garson_cagri_sayisi = len(bekleyen_garson_cagrilari)

    bekleyen_menu_talepleri = list(
        MenuSiparisTalebi.objects.filter(sube_id__in=sube_ids, durum="Beklemede")
        .select_related("sube", "masa")
        .prefetch_related("kalemler")
        .order_by("olusturma_zamani")[:8]
    )
    bekleyen_menu_talep_sayisi = len(bekleyen_menu_talepleri)

    kritik_stoklar = list(
        StokKalemi.objects.filter(sube_id__in=sube_ids, miktar__lte=F("kritik_seviye"))
        .select_related("sube")
        .order_by("miktar", "ad")[:8]
    )
    kritik_hizli_stoklar = list(
        HizliSatisUrun.objects.filter(sube_id__in=sube_ids, stok_miktari__lte=F("kritik_stok"), aktif=True)
        .select_related("sube", "urun")
        .order_by("stok_miktari", "urun__ad")[:8]
    )

    rezervasyon_sayisi = Rezervasyon.objects.filter(sube_id__in=sube_ids, tarih=today).count()
    acik_paket_sayisi = Adisyon.objects.filter(sube_id__in=sube_ids, durum="Acik", siparis_turu="Paket").count()
    acik_masa_adisyonlari = list(
        Adisyon.objects.filter(sube_id__in=sube_ids, durum="Acik", masa__isnull=False)
        .select_related("sube", "masa")
        .prefetch_related("siparisler__urun")
        .order_by("acilis_zamani")[:8]
    )

    son_siparis_aktivitesi = {
        row["siparisi_alan_id"]: row
        for row in SiparisItem.objects.filter(
            adisyon__sube_id__in=sube_ids,
            siparisi_alan__isnull=False,
            son_siparis_hareketi__isnull=False,
        )
        .values("siparisi_alan_id")
        .annotate(
            son_aktivite=Max("son_siparis_hareketi"),
            siparis_adedi=Count("id"),
        )
    }

    personel_ozeti = []
    for kayit in aktif_personel:
        profil = getattr(kayit.user, "profil", None)
        son_aktivite = son_siparis_aktivitesi.get(kayit.user_id, {})
        son_aktivite_dt = son_aktivite.get("son_aktivite")
        son_aktivite_dk = _minutes_since(son_aktivite_dt, now)
        personel_ozeti.append({
            "ad": kayit.user.get_full_name() or kayit.user.username,
            "rol": _rol_etiketi(kayit.user),
            "sube": kayit.sube.ad if kayit.sube else (getattr(profil, "sube", None).ad if getattr(profil, "sube", None) else "-"),
            "vardiya_suresi": _duration_label(kayit.toplam_sure_dakika),
            "son_siparis_hareketi": _duration_label(son_aktivite_dk) if son_aktivite_dt else "Veri yok",
            "siparis_adedi": son_aktivite.get("siparis_adedi", 0),
            "uyari": son_aktivite_dk is not None and son_aktivite_dk >= 30,
        })

    satis_ozeti = {}
    for siparis in SiparisItem.objects.filter(
        adisyon__sube_id__in=sube_ids,
        adisyon__acilis_zamani__date=today,
        iptal_edildi=False,
        ikram_mi=False,
    ).select_related("urun"):
        if siparis.urun_id not in satis_ozeti:
            satis_ozeti[siparis.urun_id] = {
                "urun": siparis.urun.ad,
                "adet": 0,
                "ciro": ZERO,
            }
        satis_ozeti[siparis.urun_id]["adet"] += siparis.adet
        satis_ozeti[siparis.urun_id]["ciro"] += Decimal(siparis.toplam_fiyat() or 0)

    en_cok_satan_urunler = sorted(
        satis_ozeti.values(),
        key=lambda item: (item["adet"], item["ciro"]),
        reverse=True,
    )[:8]

    branch_ciro_today = defaultdict(lambda: ZERO)
    branch_ciro_yesterday = defaultdict(lambda: ZERO)
    for adisyon in adisyon_today:
        branch_ciro_today[adisyon.sube_id] += _adisyon_total(adisyon)
    for satis in quick_sales_today:
        branch_ciro_today[satis.sube_id] += Decimal(satis.toplam_tutar or 0)
    for adisyon in adisyon_yesterday:
        branch_ciro_yesterday[adisyon.sube_id] += _adisyon_total(adisyon)
    for satis in quick_sales_yesterday:
        branch_ciro_yesterday[satis.sube_id] += Decimal(satis.toplam_tutar or 0)

    aktif_masa_map = {row["sube_id"]: row["toplam"] for row in Masa.objects.filter(sube_id__in=sube_ids, dolu_mu=True).values("sube_id").annotate(toplam=Count("id"))}
    toplam_masa_map = {row["sube_id"]: row["toplam"] for row in Masa.objects.filter(sube_id__in=sube_ids).values("sube_id").annotate(toplam=Count("id"))}
    mutfak_map = {row["adisyon__sube_id"]: row["toplam"] for row in SiparisItem.objects.filter(adisyon__sube_id__in=sube_ids, adisyon__durum="Acik", hazir_mi=False, iptal_edildi=False).values("adisyon__sube_id").annotate(toplam=Count("id"))}
    cagri_map = {row["sube_id"]: row["toplam"] for row in GarsonCagri.objects.filter(sube_id__in=sube_ids, tamamlandi_mi=False).values("sube_id").annotate(toplam=Count("id"))}
    menu_map = {row["sube_id"]: row["toplam"] for row in MenuSiparisTalebi.objects.filter(sube_id__in=sube_ids, durum="Beklemede").values("sube_id").annotate(toplam=Count("id"))}
    bolge_map = {
        row["urun__bolge_id"]: row["toplam"]
        for row in SiparisItem.objects.filter(
            adisyon__sube_id__in=sube_ids,
            adisyon__durum="Acik",
            hazir_mi=False,
            iptal_edildi=False,
            urun__bolge__isnull=False,
        ).values("urun__bolge_id").annotate(toplam=Count("id"))
    }

    sube_pulse = []
    for sube in subeler:
        bugun_ciro = branch_ciro_today[sube.id]
        dunden_ciro = branch_ciro_yesterday[sube.id]
        sube_pulse.append({
            "ad": sube.ad,
            "ciro": _format_currency(bugun_ciro),
            "delta": _format_percent(_delta_percent(bugun_ciro, dunden_ciro)),
            "aktif_masa": aktif_masa_map.get(sube.id, 0),
            "toplam_masa": toplam_masa_map.get(sube.id, 0),
            "bekleyen_mutfak": mutfak_map.get(sube.id, 0),
            "garson_cagri": cagri_map.get(sube.id, 0),
            "menu_onay": menu_map.get(sube.id, 0),
        })

    bolge_pulse = []
    for bolge in Bolge.objects.filter(sube_id__in=sube_ids).select_related("sube").order_by("sube__ad", "ad"):
        bolge_pulse.append({
            "id": bolge.id,
            "ad": bolge.ad,
            "sube": bolge.sube.ad,
            "bekleyen": bolge_map.get(bolge.id, 0),
            "durum": "Yogun" if bolge_map.get(bolge.id, 0) else "Temiz",
            "url": reverse("mutfak_ekrani_filtreli", args=[bolge.id]),
        })

    operasyon_uyarilari = []
    if aktif_personel_sayisi == 0:
        operasyon_uyarilari.append({"seviye": "danger", "metin": "Aktif vardiyada personel gorunmuyor."})
    if bekleyen_garson_cagri_sayisi:
        en_eski_cagri_dk = _minutes_since(bekleyen_garson_cagrilari[0].zaman, now)
        operasyon_uyarilari.append({"seviye": "warning", "metin": f"{bekleyen_garson_cagri_sayisi} garson cagrisi bekliyor. En eskisi {_duration_label(en_eski_cagri_dk)} once."})
    if bekleyen_menu_talep_sayisi:
        en_eski_menu_dk = _minutes_since(bekleyen_menu_talepleri[0].olusturma_zamani, now)
        operasyon_uyarilari.append({"seviye": "warning", "metin": f"{bekleyen_menu_talep_sayisi} QR/menu siparisi onay bekliyor. En eskisi {_duration_label(en_eski_menu_dk)} once geldi."})
    if kritik_stoklar or kritik_hizli_stoklar:
        operasyon_uyarilari.append({"seviye": "danger", "metin": f"{len(kritik_stoklar) + len(kritik_hizli_stoklar)} kritik stok kalemi dikkat istiyor."})
    if Decimal(ciro_today or 0) < Decimal(ciro_yesterday or 0):
        operasyon_uyarilari.append({"seviye": "info", "metin": f"Bugunku ciro dunden dusuk gorunuyor ({_format_percent(ciro_delta)})." })

    metric_cards = [
        {
            "title": "Gunluk Ciro",
            "value": f"{_format_currency(ciro_today)} TL",
            "meta": f"Dune gore {_format_percent(ciro_delta)}",
            "icon": "bi-cash-coin",
            "tone": "primary",
            "url": None,
        },
        {
            "title": "Aktif Personel",
            "value": str(aktif_personel_sayisi),
            "meta": f"Toplam aktif kayit {toplam_aktif_personel}",
            "icon": "bi-people-fill",
            "tone": "teal",
            "url": None,
        },
        {
            "title": "Bekleyen Mutfak",
            "value": str(bekleyen_mutfak_sayisi),
            "meta": f"En eski siparis {_duration_label(mutfak_bekleme_dakika)} once",
            "icon": "bi-fire",
            "tone": "warm",
            "url": f"{reverse('mutfak_ana_sayfa')}?next={reverse('yonetim_paneli')}",
        },
        {
            "title": "Garson Cagrisi",
            "value": str(bekleyen_garson_cagri_sayisi),
            "meta": "Salon talepleri beklemede",
            "icon": "bi-bell-fill",
            "tone": "danger",
            "url": f"{reverse('garson_paneli')}?next={reverse('yonetim_paneli')}",
        },
        {
            "title": "Kritik Stok",
            "value": str(len(kritik_stoklar) + len(kritik_hizli_stoklar)),
            "meta": "Acil tedarik takibi",
            "icon": "bi-exclamation-triangle-fill",
            "tone": "dark",
            "url": None,
        },
        {
            "title": "Bekleyen QR Siparis",
            "value": str(bekleyen_menu_talep_sayisi),
            "meta": "Masalardan gelen menu talepleri",
            "icon": "bi-clipboard2-check-fill",
            "tone": "secondary",
            "url": f"{reverse('menu_siparis_onay_listesi')}?next={reverse('yonetim_paneli')}",
        },
    ]

    return {
        **dashboard_links,
        "sube_kapsami": subeler,
        "metric_cards": metric_cards,
        "ciro_today": _format_currency(ciro_today),
        "ciro_yesterday": _format_currency(ciro_yesterday),
        "ciro_delta": _format_percent(ciro_delta),
        "hesap_sayisi_today": hesap_sayisi_today,
        "ortalama_sepet": _format_currency(ortalama_sepet),
        "aktif_masa_sayisi": aktif_masa_sayisi,
        "toplam_masa_sayisi": toplam_masa_sayisi,
        "doluluk_orani": doluluk_orani,
        "rezervasyon_sayisi": rezervasyon_sayisi,
        "acik_paket_sayisi": acik_paket_sayisi,
        "bekleyen_mutfak_siparisleri": [
            {
                "urun": item.urun.ad,
                "sube": item.adisyon.sube.ad if item.adisyon and item.adisyon.sube else "-",
                "masa": item.adisyon.masa.masa_no if item.adisyon and item.adisyon.masa else "Paket",
                "adet": item.adet,
                "bekleme": _duration_label(_minutes_since(item.eklenme_zamani, now)),
            }
            for item in bekleyen_mutfak_siparisleri
        ],
        "mutfak_durumu": {
            "bekleyen_sayi": bekleyen_mutfak_sayisi,
            "bekleme": _duration_label(mutfak_bekleme_dakika) if bekleyen_mutfak_sayisi else "Kuyruk temiz",
            "bosta_sure": _duration_label(mutfak_bosta_dakika) if mutfak_bosta_dakika is not None else "Veri yok",
        },
        "bekleyen_garson_cagrilari": [
            {
                "sube": cagri.sube.ad,
                "masa": cagri.masa_no,
                "bekleme": _duration_label(_minutes_since(cagri.zaman, now)),
            }
            for cagri in bekleyen_garson_cagrilari
        ],
        "bekleyen_menu_talepleri": [
            {
                "sube": talep.sube.ad,
                "masa": talep.masa_no,
                "kalem": talep.kalemler.count(),
                "toplam": _format_currency(talep.toplam_tutar()),
                "bekleme": _duration_label(_minutes_since(talep.olusturma_zamani, now)),
            }
            for talep in bekleyen_menu_talepleri
        ],
        "aktif_masa_ozeti": [
            {
                "sube": adisyon.sube.ad if adisyon.sube else "-",
                "masa": adisyon.masa.masa_no if adisyon.masa else "-",
                "sure": _duration_label(_minutes_since(adisyon.acilis_zamani, now)),
                "tutar": _format_currency(_adisyon_total(adisyon)),
                "siparis_adedi": sum(item.adet for item in adisyon.siparisler.all() if not item.iptal_edildi),
            }
            for adisyon in acik_masa_adisyonlari
        ],
        "en_cok_satan_urunler": [
            {
                "urun": item["urun"],
                "adet": item["adet"],
                "ciro": _format_currency(item["ciro"]),
            }
            for item in en_cok_satan_urunler
        ],
        "personel_ozeti": personel_ozeti,
        "stok_uyarilari": [
            {
                "sube": stok.sube.ad,
                "ad": stok.ad,
                "miktar": f"{stok.miktar} {stok.birim}",
                "kritik": f"{stok.kritik_seviye} {stok.birim}",
                "tur": "Stok",
            }
            for stok in kritik_stoklar
        ] + [
            {
                "sube": urun.sube.ad,
                "ad": urun.urun.ad,
                "miktar": f"{urun.stok_miktari}",
                "kritik": f"{urun.kritik_stok}",
                "tur": "Hizli Satis",
            }
            for urun in kritik_hizli_stoklar
        ],
        "sube_pulse": sube_pulse,
        "bolge_pulse": bolge_pulse,
        "operasyon_uyarilari": operasyon_uyarilari,
        "quick_links": dashboard_links["management_tools"] + dashboard_links["sube_cards"],
    }


@login_required
@user_passes_test(yonetici_mi)
def yonetim_paneli(request):
    context = _build_manager_dashboard_context(request.user)
    return render(request, "adisyon_modulu/yonetim_paneli.html", context)
