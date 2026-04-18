from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from adisyon_modulu.models import (
    Alerjen,
    Bolge,
    HizliSatisUrun,
    Kategori,
    Sube,
    Urun,
)


# ===============================
# YARDIMCI FONKSİYONLAR
# ===============================
def urun_yonetim_yetki_kontrol(user):
    return user.is_superuser or getattr(user.profil, "rol", "") in ["Yonetici", "Muhasebe"]


def parse_decimal(value, default=None):
    value = (value or "").strip()
    if not value:
        return default
    try:
        return Decimal(value.replace(",", "."))
    except (InvalidOperation, AttributeError):
        raise InvalidOperation


# ===============================
# ÜRÜN LİSTE
# ===============================
@login_required
def urun_listesi(request):
    if not urun_yonetim_yetki_kontrol(request.user):
        return redirect("ana_sayfa")

    urunler = (
        Urun.objects.select_related("kategori", "bolge")
        .prefetch_related("hizli_satis_urunleri")
        .order_by("sira", "-id")
    )

    return render(
        request,
        "adisyon_modulu/urunler/urun_listesi.html",
        {
            "page_obj": urunler,
            "kategoriler": Kategori.objects.all(),
            "subeler": Sube.objects.all(),
            "filtreler": {},
        },
    )


# ===============================
# ÜRÜN EKLE
# ===============================
@login_required
def urun_ekle(request):
    if not urun_yonetim_yetki_kontrol(request.user):
        return redirect("ana_sayfa")

    if request.method == "POST":
        ad = request.POST.get("ad", "").strip()
        kategori_id = request.POST.get("kategori") or None
        kdv_orani = request.POST.get("kdv_orani") or 10
        bolge_id = request.POST.get("bolge") or None
        aciklama = request.POST.get("aciklama", "")
        alerjen_bilgisi = request.POST.get("alerjen_bilgisi", "")
        gorsel = request.FILES.get("gorsel")

        try:
            fiyat = parse_decimal(request.POST.get("fiyat"), Decimal("0"))
        except InvalidOperation:
            messages.error(request, "Fiyat formatı hatalı.")
            return redirect("urun_ekle")

        if not ad:
            messages.error(request, "Ürün adı zorunludur.")
            return redirect("urun_ekle")

        # Hızlı satış alanları
        hizli_satis_aktif = bool(request.POST.get("hizli_satis_aktif"))
        hs_sube = request.POST.get("hs_sube") or None
        barkod = request.POST.get("barkod", "").strip()

        if hizli_satis_aktif:
            if not hs_sube:
                messages.error(request, "Hızlı satış için şube seçmelisiniz.")
                return redirect("urun_ekle")

            if not barkod:
                messages.error(request, "Hızlı satış için barkod zorunludur.")
                return redirect("urun_ekle")

            if HizliSatisUrun.objects.filter(barkod=barkod).exists():
                messages.error(request, "Bu barkod zaten kullanılıyor.")
                return redirect("urun_ekle")

            try:
                satis_fiyati = parse_decimal(request.POST.get("satis_fiyati"), fiyat)
                indirimli_fiyat = parse_decimal(request.POST.get("indirimli_fiyat"), None)
                stok_miktari = parse_decimal(request.POST.get("stok_miktari"), Decimal("0"))
                kritik_stok = parse_decimal(request.POST.get("kritik_stok"), Decimal("5"))
            except InvalidOperation:
                messages.error(request, "Hızlı satış fiyat/stok formatı hatalı.")
                return redirect("urun_ekle")

        urun = Urun.objects.create(
            ad=ad,
            kategori_id=kategori_id,
            fiyat=fiyat,
            kdv_orani=kdv_orani,
            bolge_id=bolge_id,
            aciklama=aciklama,
            alerjen_bilgisi=alerjen_bilgisi,
            gorsel=gorsel,
        )

        secili_alerjenler = request.POST.getlist("alerjenler")
        urun.alerjenler.set(secili_alerjenler)

        if hizli_satis_aktif:
            HizliSatisUrun.objects.create(
                urun=urun,
                sube_id=hs_sube,
                barkod=barkod,
                barkod_tipi=request.POST.get("barkod_tipi") or "EAN13",
                satis_fiyati=satis_fiyati,
                indirimli_fiyat=indirimli_fiyat,
                stok_miktari=stok_miktari,
                kritik_stok=kritik_stok,
                indirimde_mi=bool(request.POST.get("indirimde_mi")),
                aktif=bool(request.POST.get("hs_aktif")),
            )

        messages.success(request, "Ürün eklendi.")
        return redirect("urun_listesi")

    return render(
        request,
        "adisyon_modulu/urunler/urun_form.html",
        {
            "kategoriler": Kategori.objects.all(),
            "bolgeler": Bolge.objects.select_related("sube"),
            "subeler": Sube.objects.all(),
            "alerjenler": Alerjen.objects.filter(aktif=True).order_by("ad"),
            "fiyat_value": "",
            "sayfa_baslik": "Yeni Ürün",
        },
    )


# ===============================
# ÜRÜN DÜZENLE
# ===============================
@login_required
def urun_duzenle(request, urun_id):
    if not urun_yonetim_yetki_kontrol(request.user):
        return redirect("ana_sayfa")

    urun = get_object_or_404(Urun, id=urun_id)
    hizli_satis_urun = urun.hizli_satis_urunleri.first()

    if request.method == "POST":
        ad = request.POST.get("ad", "").strip()
        kategori_id = request.POST.get("kategori") or None
        kdv_orani = request.POST.get("kdv_orani") or 10
        bolge_id = request.POST.get("bolge") or None
        aciklama = request.POST.get("aciklama", "")
        alerjen_bilgisi = request.POST.get("alerjen_bilgisi", "")

        if not ad:
            messages.error(request, "Ürün adı zorunludur.")
            return redirect("urun_duzenle", urun_id=urun.id)

        try:
            fiyat = parse_decimal(request.POST.get("fiyat"), urun.fiyat)
        except InvalidOperation:
            messages.error(request, "Fiyat formatı hatalı.")
            return redirect("urun_duzenle", urun_id=urun.id)

        urun.ad = ad
        urun.kategori_id = kategori_id
        urun.kdv_orani = kdv_orani
        urun.bolge_id = bolge_id
        urun.aciklama = aciklama
        urun.alerjen_bilgisi = alerjen_bilgisi
        urun.fiyat = fiyat

        if request.FILES.get("gorsel"):
            urun.gorsel = request.FILES.get("gorsel")

        urun.save()

        secili_alerjenler = request.POST.getlist("alerjenler")
        urun.alerjenler.set(secili_alerjenler)

        hizli_satis_aktif = bool(request.POST.get("hizli_satis_aktif"))
        hs_sube = request.POST.get("hs_sube") or None
        barkod = request.POST.get("barkod", "").strip()

        if hizli_satis_aktif:
            if not hs_sube:
                messages.error(request, "Hızlı satış için şube seçmelisiniz.")
                return redirect("urun_duzenle", urun_id=urun.id)

            if not barkod:
                messages.error(request, "Hızlı satış için barkod zorunludur.")
                return redirect("urun_duzenle", urun_id=urun.id)

            barkod_qs = HizliSatisUrun.objects.filter(barkod=barkod)
            if hizli_satis_urun:
                barkod_qs = barkod_qs.exclude(id=hizli_satis_urun.id)
            if barkod_qs.exists():
                messages.error(request, "Bu barkod zaten kullanılıyor.")
                return redirect("urun_duzenle", urun_id=urun.id)

            try:
                satis_fiyati = parse_decimal(request.POST.get("satis_fiyati"), urun.fiyat)
                indirimli_fiyat = parse_decimal(request.POST.get("indirimli_fiyat"), None)
                stok_miktari = parse_decimal(request.POST.get("stok_miktari"), Decimal("0"))
                kritik_stok = parse_decimal(request.POST.get("kritik_stok"), Decimal("5"))
            except InvalidOperation:
                messages.error(request, "Hızlı satış fiyat/stok formatı hatalı.")
                return redirect("urun_duzenle", urun_id=urun.id)

            if not hizli_satis_urun:
                hizli_satis_urun = HizliSatisUrun(urun=urun)

            hizli_satis_urun.sube_id = hs_sube
            hizli_satis_urun.barkod = barkod
            hizli_satis_urun.barkod_tipi = request.POST.get("barkod_tipi") or "EAN13"
            hizli_satis_urun.satis_fiyati = satis_fiyati
            hizli_satis_urun.indirimli_fiyat = indirimli_fiyat
            hizli_satis_urun.stok_miktari = stok_miktari
            hizli_satis_urun.kritik_stok = kritik_stok
            hizli_satis_urun.indirimde_mi = bool(request.POST.get("indirimde_mi"))
            hizli_satis_urun.aktif = bool(request.POST.get("hs_aktif"))
            hizli_satis_urun.save()
        else:
            if hizli_satis_urun:
                hizli_satis_urun.delete()

        messages.success(request, "Ürün güncellendi.")
        return redirect("urun_listesi")

    return render(
        request,
        "adisyon_modulu/urunler/urun_form.html",
        {
            "urun": urun,
            "hizli_satis_urun": hizli_satis_urun,
            "kategoriler": Kategori.objects.all(),
            "bolgeler": Bolge.objects.select_related("sube"),
            "subeler": Sube.objects.all(),
            "alerjenler": Alerjen.objects.filter(aktif=True).order_by("ad"),
            "fiyat_value": urun.fiyat,
            "sayfa_baslik": "Ürün Düzenle",
        },
    )


# ===============================
# ÜRÜN SİL
# ===============================
@login_required
def urun_sil(request, urun_id):
    if not urun_yonetim_yetki_kontrol(request.user):
        return redirect("ana_sayfa")

    urun = get_object_or_404(Urun, id=urun_id)

    if request.method == "POST":
        urun.delete()
        messages.success(request, "Ürün silindi.")

    return redirect("urun_listesi")


# ===============================
# KATEGORİ
# ===============================
@login_required
def kategori_listesi(request):
    return render(
        request,
        "adisyon_modulu/urunler/kategori_listesi.html",
        {"kategoriler": Kategori.objects.all().order_by("sira", "ad")},
    )


@login_required
def kategori_ekle(request):
    if request.method == "POST":
        Kategori.objects.create(
            ad=request.POST.get("ad"),
            sira=request.POST.get("sira") or 0,
        )
        return redirect("kategori_listesi")

    return render(request, "adisyon_modulu/urunler/kategori_form.html")


@login_required
def kategori_duzenle(request, kategori_id):
    kategori = get_object_or_404(Kategori, id=kategori_id)

    if request.method == "POST":
        kategori.ad = request.POST.get("ad")
        kategori.sira = request.POST.get("sira") or 0
        kategori.save()
        return redirect("kategori_listesi")

    return render(
        request,
        "adisyon_modulu/urunler/kategori_form.html",
        {"kategori": kategori},
    )


@login_required
def kategori_sil(request, kategori_id):
    kategori = get_object_or_404(Kategori, id=kategori_id)

    if request.method == "POST":
        kategori.delete()

    return redirect("kategori_listesi")


# ===============================
# ALERJEN
# ===============================
@login_required
def alerjen_listesi(request):
    return render(
        request,
        "adisyon_modulu/urunler/alerjen_listesi.html",
        {"alerjenler": Alerjen.objects.all()},
    )


@login_required
def alerjen_ekle(request):
    if request.method == "POST":
        Alerjen.objects.create(ad=request.POST.get("ad"))
        return redirect("alerjen_listesi")

    return render(request, "adisyon_modulu/urunler/alerjen_form.html")


@login_required
def alerjen_duzenle(request, pk):
    alerjen = get_object_or_404(Alerjen, id=pk)

    if request.method == "POST":
        alerjen.ad = request.POST.get("ad")
        alerjen.aktif = bool(request.POST.get("aktif"))
        alerjen.save()
        return redirect("alerjen_listesi")

    return render(
        request,
        "adisyon_modulu/urunler/alerjen_form.html",
        {"alerjen": alerjen},
    )


@login_required
def alerjen_sil(request, pk):
    alerjen = get_object_or_404(Alerjen, id=pk)

    if request.method == "POST":
        alerjen.delete()

    return redirect("alerjen_listesi")