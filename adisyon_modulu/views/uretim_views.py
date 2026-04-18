from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from ..models import (
    HizliSatisUrun,
    Recete,
    Sube,
    StokHareket,
    StokKalemi,
    UretimFis,
    Urun,
)


@login_required
def uretim_ekrani(request):
    subeler = Sube.objects.all().order_by("ad")
    urunler = (
        Urun.objects.filter(receteli_mi=True)
        .select_related("kategori", "bolge")
        .order_by("ad")
    )

    son_uretimler = (
        UretimFis.objects.select_related("sube", "urun", "olusturan")
        .order_by("-tarih")[:20]
    )

    context = {
        "subeler": subeler,
        "urunler": urunler,
        "son_uretimler": son_uretimler,
    }
    return render(request, "adisyon_modulu/uretim/uretim_ekrani.html", context)


@login_required
@transaction.atomic
def uretim_kaydet(request):
    if request.method != "POST":
        return redirect("uretim_ekrani")

    sube_id = request.POST.get("sube")
    urun_id = request.POST.get("urun")
    miktar_raw = (request.POST.get("miktar") or "").strip()
    aciklama = (request.POST.get("aciklama") or "").strip()

    if not sube_id or not urun_id or not miktar_raw:
        messages.error(request, "Şube, ürün ve miktar zorunludur.")
        return redirect("uretim_ekrani")

    try:
        miktar = Decimal(miktar_raw.replace(",", "."))
    except (InvalidOperation, ValueError):
        messages.error(request, "Miktar sayısal bir değer olmalıdır.")
        return redirect("uretim_ekrani")

    if miktar <= 0:
        messages.error(request, "Üretim miktarı 0'dan büyük olmalıdır.")
        return redirect("uretim_ekrani")

    sube = get_object_or_404(Sube, id=sube_id)
    urun = get_object_or_404(Urun, id=urun_id)

    receteler = list(
        Recete.objects.filter(urun=urun)
        .select_related("stok_item")
        .order_by("stok_item__ad")
    )

    if not receteler:
        messages.error(request, "Bu ürün için reçete tanımlı değil.")
        return redirect("uretim_ekrani")

    uretim_fis = UretimFis.objects.create(
        sube=sube,
        urun=urun,
        miktar=miktar,
        aciklama=aciklama,
        olusturan=request.user,
    )

    eksiye_dusenler = []

    # 1) Reçetedeki hammaddeleri stoktan düş
    for recete in receteler:
        stok = recete.stok_item

        if hasattr(stok, "sube") and stok.sube_id != sube.id:
            continue

        tuketim_miktari = Decimal(str(recete.miktar)) * miktar
        mevcut_miktar = Decimal(str(stok.miktar or 0))
        yeni_miktar = mevcut_miktar - tuketim_miktari

        if hasattr(stok, "miktar_guncelle"):
            stok.miktar_guncelle(
                yeni_miktar=yeni_miktar,
                tip="cikis",
                kullanici=request.user,
                aciklama=f"Üretim için düşüldü - {urun.ad} / Fiş No: {uretim_fis.id}",
            )
            stok.refresh_from_db(fields=["miktar"])
        else:
            stok.miktar = yeni_miktar
            stok.save(update_fields=["miktar"])

            try:
                StokHareket.objects.create(
                    stok=stok,
                    tip="cikis",
                    miktar=tuketim_miktari,
                    onceki_miktar=mevcut_miktar,
                    sonraki_miktar=stok.miktar,
                    aciklama=f"Üretim için düşüldü - {urun.ad} / Fiş No: {uretim_fis.id}",
                    kullanici=request.user,
                )
            except Exception:
                pass

        if Decimal(str(stok.miktar or 0)) < 0:
            eksiye_dusenler.append(stok.ad)

    # 2) Üretilen ürünü hızlı satış stokuna ekle
    hizli_satis_urun = HizliSatisUrun.objects.filter(
        sube=sube,
        urun=urun
    ).first()

    if hizli_satis_urun:
        onceki_hizli_satis_stok = Decimal(str(hizli_satis_urun.stok_miktari or 0))
        hizli_satis_urun.stok_miktari = onceki_hizli_satis_stok + miktar
        hizli_satis_urun.save(update_fields=["stok_miktari"])
    else:
        HizliSatisUrun.objects.create(
            sube=sube,
            urun=urun,
            barkod="",
            satis_fiyati=urun.fiyat or 0,
            stok_miktari=miktar,
            aktif=False,
        )

    # 3) Mamul stok kartını artır / yoksa oluştur
    mamul_stok = StokKalemi.objects.filter(
        sube=sube,
        ad__iexact=urun.ad
    ).first()

    if mamul_stok:
        mevcut_mamul_miktar = Decimal(str(mamul_stok.miktar or 0))
        yeni_mamul_miktar = mevcut_mamul_miktar + miktar

        # mamul stok satılabilir olsun
        if hasattr(mamul_stok, "satilabilir_mi"):
            mamul_stok.satilabilir_mi = True
        if hasattr(mamul_stok, "uretimde_kullanilir_mi"):
            mamul_stok.uretimde_kullanilir_mi = False

        if hasattr(mamul_stok, "miktar_guncelle"):
            mamul_stok.miktar_guncelle(
                yeni_miktar=yeni_mamul_miktar,
                tip="giris",
                kullanici=request.user,
                aciklama=f"Üretimden mamul girişi - {urun.ad} / Fiş No: {uretim_fis.id}",
            )
            # miktar_guncelle diğer alanları save etmiyorsa garantiye al
            mamul_stok.save()
        else:
            mamul_stok.miktar = yeni_mamul_miktar
            mamul_stok.save()

            try:
                StokHareket.objects.create(
                    stok=mamul_stok,
                    tip="giris",
                    miktar=miktar,
                    onceki_miktar=mevcut_mamul_miktar,
                    sonraki_miktar=mamul_stok.miktar,
                    aciklama=f"Üretimden mamul girişi - {urun.ad} / Fiş No: {uretim_fis.id}",
                    kullanici=request.user,
                )
            except Exception:
                pass
    else:
        # hiç mamul stok kartı yoksa otomatik oluştur
        mamul_stok = StokKalemi.objects.create(
            sube=sube,
            ad=urun.ad,
            miktar=Decimal("0"),
            birim="adet",
            kritik_seviye=Decimal("0"),
            fiyat=urun.fiyat or 0,
            barkod="",
            satilabilir_mi=True,
            uretimde_kullanilir_mi=False,
            otomatik_urun_olustur=False,
        )

        if hasattr(mamul_stok, "miktar_guncelle"):
            mamul_stok.miktar_guncelle(
                yeni_miktar=miktar,
                tip="giris",
                kullanici=request.user,
                aciklama=f"Üretimden mamul stok kartı oluşturuldu - {urun.ad} / Fiş No: {uretim_fis.id}",
            )
            mamul_stok.refresh_from_db(fields=["miktar"])
        else:
            mamul_stok.miktar = miktar
            mamul_stok.save(update_fields=["miktar"])

            try:
                StokHareket.objects.create(
                    stok=mamul_stok,
                    tip="giris",
                    miktar=miktar,
                    onceki_miktar=Decimal("0"),
                    sonraki_miktar=mamul_stok.miktar,
                    aciklama=f"Üretimden mamul stok kartı oluşturuldu - {urun.ad} / Fiş No: {uretim_fis.id}",
                    kullanici=request.user,
                )
            except Exception:
                pass

    if eksiye_dusenler:
        messages.warning(
            request,
            "Üretim kaydedildi. Eksi stoğa düşen hammaddeler: " + ", ".join(eksiye_dusenler)
        )
    else:
        messages.success(request, "Üretim başarıyla kaydedildi.")

    return redirect("uretim_ekrani")