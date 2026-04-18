# views/stok_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test  # BU ÖNEMLİ!
from django.contrib import messages

from ..models import Sube, Tedarikci, StokKalemi
from .auth_views import yonetici_mi 
from django.shortcuts import render
from django.core.files.storage import FileSystemStorage
from django.contrib import messages

from adisyon_modulu.services.xml_fatura import xml_fatura_aktar
from decimal import Decimal
from django.shortcuts import get_object_or_404, redirect
from adisyon_modulu.models import StokKalemi, XMLUrunEsleme, Tedarikci, Sube
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import FileSystemStorage
from django.contrib import messages

from adisyon_modulu.models import StokKalemi
from adisyon_modulu.services.xml_fatura import xml_fatura_aktar
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect

from adisyon_modulu.models import StokKalemi
from adisyon_modulu.models import Urun, Kategori
from adisyon_modulu.models import HizliSatisUrun
from adisyon_modulu.models import Recete

@login_required
@user_passes_test(yonetici_mi)
def tedarikci_listesi(request):
    """Tedarikçi listesini göster"""
    sube_id = request.GET.get('sube')
    
    tedarikciler = Tedarikci.objects.all()
    if sube_id:
        tedarikciler = tedarikciler.filter(sube_id=sube_id)
    
    context = {
        'tedarikciler': tedarikciler,
        'subeler': Sube.objects.all(),
        'secili_sube': sube_id,
    }
    return render(request, 'adisyon_modulu/tedarikci_listesi.html', context)


@login_required
@user_passes_test(yonetici_mi)
def tedarikci_ekle(request):
    """Yeni tedarikçi ekle"""
    if request.method == "POST":
        sube = get_object_or_404(Sube, id=request.POST.get('sube_id'))
        
        tedarikci = Tedarikci.objects.create(
            sube=sube,
            ad=request.POST.get('ad'),
            yetkili=request.POST.get('yetkili'),
            telefon=request.POST.get('telefon'),
            email=request.POST.get('email'),
            adres=request.POST.get('adres'),
            vergi_no=request.POST.get('vergi_no'),
            notlar=request.POST.get('notlar'),
            aktif=True
        )
        messages.success(request, f"{tedarikci.ad} başarıyla eklendi.")
        return redirect('tedarikci_listesi')
    
    subeler = Sube.objects.all()
    return render(request, 'adisyon_modulu/tedarikci_ekle.html', {'subeler': subeler})


@login_required
@user_passes_test(yonetici_mi)
def tedarikci_duzenle(request, tedarikci_id):
    """Tedarikçi bilgilerini düzenle"""
    tedarikci = get_object_or_404(Tedarikci, id=tedarikci_id)
    
    if request.method == "POST":
        tedarikci.ad = request.POST.get('ad')
        tedarikci.yetkili = request.POST.get('yetkili')
        tedarikci.telefon = request.POST.get('telefon')
        tedarikci.email = request.POST.get('email')
        tedarikci.adres = request.POST.get('adres')
        tedarikci.vergi_no = request.POST.get('vergi_no')
        tedarikci.notlar = request.POST.get('notlar')
        tedarikci.aktif = request.POST.get('aktif') == 'on'
        tedarikci.save()
        
        messages.success(request, f"{tedarikci.ad} güncellendi.")
        return redirect('tedarikci_listesi')
    
    subeler = Sube.objects.all()
    return render(request, 'adisyon_modulu/tedarikci_duzenle.html', {
        'tedarikci': tedarikci,
        'subeler': subeler
    })


@login_required
@user_passes_test(yonetici_mi)
def tedarikci_sil(request, tedarikci_id):
    """Tedarikçi sil"""
    tedarikci = get_object_or_404(Tedarikci, id=tedarikci_id)
    tedarikci.delete()
    messages.success(request, f"{tedarikci.ad} silindi.")
    return redirect('tedarikci_listesi')


@login_required
@user_passes_test(yonetici_mi)
def stok_giris(request, stok_id):
    """Stok girişi yap"""
    stok = get_object_or_404(StokKalemi, id=stok_id)
    
    if request.method == "POST":
        miktar = float(request.POST.get('miktar', 0))
        aciklama = request.POST.get('aciklama', '')
        
        if miktar > 0:
            yeni_miktar = stok.miktar + miktar
            if hasattr(stok, 'miktar_guncelle'):
                stok.miktar_guncelle(
                    yeni_miktar=yeni_miktar,
                    tip='giris',
                    kullanici=request.user,
                    aciklama=aciklama
                )
            else:
                stok.miktar = yeni_miktar
                stok.save()
            messages.success(request, f"{stok.ad} stokuna {miktar} {stok.birim} eklendi.")
        else:
            messages.error(request, "Geçersiz miktar!")
        
        # Stok listesi sayfasına yönlendir (henüz yoksa admin panele)
        return redirect('/admin/adisyon_modulu/stokkalemi/')
    
    return render(request, 'adisyon_modulu/stok_giris.html', {'stok': stok})

def xml_fatura_yukle(request):
    stoklar = StokKalemi.objects.all().order_by("ad")

    if request.method == "POST" and request.FILES.get("xml"):
        xml_file = request.FILES["xml"]

        if not xml_file.name.lower().endswith(".xml"):
            messages.error(request, "Lütfen .xml dosyası yükleyin.")
            return render(request, "adisyon_modulu/xml_yukle.html", {
                "stoklar": stoklar,
                "eslesmeyen": [],
            })

        fs = FileSystemStorage()
        filename = fs.save(f"xml_faturalar/{xml_file.name}", xml_file)
        path = fs.path(filename)

        try:
            eklenen, eslesmeyen = xml_fatura_aktar(path)
            request.session["son_eslesmeyenler"] = eslesmeyen

            messages.success(
                request,
                f"{len(eklenen)} stok eklendi, {len(eslesmeyen)} eşleşmedi."
            )

            return render(request, "adisyon_modulu/xml_yukle.html", {
                "stoklar": stoklar,
                "eslesmeyen": eslesmeyen,
                "eklenen": eklenen,
            })

        except Exception as e:
            messages.error(request, f"XML okunamadı: {e}")
            return render(request, "adisyon_modulu/xml_yukle.html", {
                "stoklar": stoklar,
                "eslesmeyen": [],
            })

    return render(request, "adisyon_modulu/xml_yukle.html", {
        "stoklar": stoklar,
        "eslesmeyen": request.session.get("son_eslesmeyenler", []),
    })

def xml_eslesme_kaydet(request):
    if request.method != "POST":
        return redirect("xml_yukle")

    yeni_stok = request.POST.get("yeni_stok") == "1"
    satilabilir_yeni_stok = request.POST.get("satilabilir_yeni_stok") == "1"
    stok_id = request.POST.get("stok_id")
    yeni_stok_adi = (request.POST.get("yeni_stok_adi") or "").strip()

    xml_urun_adi = (request.POST.get("xml_urun_adi") or "").strip()
    xml_barkod = (request.POST.get("xml_barkod") or "").strip()
    miktar_raw = (request.POST.get("miktar") or "0").strip()
    fiyat_raw = (request.POST.get("fiyat") or "0").strip()
    birim = (request.POST.get("birim") or "adet").strip()

    try:
        miktar = Decimal(miktar_raw.replace(",", "."))
    except Exception:
        miktar = Decimal("0")

    try:
        fiyat = Decimal(fiyat_raw.replace(",", "."))
    except Exception:
        fiyat = Decimal("0")

    if miktar <= 0:
        messages.error(request, "Geçersiz miktar.")
        return redirect("xml_yukle")

    stok = None
    olusan_urun = None

    if yeni_stok:
        if not yeni_stok_adi:
            messages.error(request, "Yeni stok adı boş olamaz.")
            return redirect("xml_yukle")

        sube = Sube.objects.first()
        if not sube:
            messages.error(request, "Önce en az bir şube tanımlamalısınız.")
            return redirect("xml_yukle")

        stok = StokKalemi.objects.create(
            sube=sube,
            ad=yeni_stok_adi,
            miktar=miktar,
            birim=birim,
            kritik_seviye=Decimal("1"),
            fiyat=fiyat,
            barkod=xml_barkod or None,
            satilabilir_mi=satilabilir_yeni_stok,
            uretimde_kullanilir_mi=not satilabilir_yeni_stok,
            otomatik_urun_olustur=satilabilir_yeni_stok,
        )
        if satilabilir_yeni_stok:
            olusan_urun = stoktan_urun_olustur(stok)
            if olusan_urun:
                urunu_hizli_satisa_ekle(olusan_urun, stok)
                
        from adisyon_modulu.models import StokHareket
        StokHareket.objects.create(
            stok=stok,
            tip="giris",
            miktar=miktar,
            onceki_miktar=Decimal("0"),
            sonraki_miktar=miktar,
            aciklama=f"XML'den yeni stok kartı açıldı - XML Ürün: {xml_urun_adi}",
            kullanici=request.user if request.user.is_authenticated else None,
        )

    else:
        if not stok_id:
            messages.error(request, "Lütfen bir stok seçin.")
            return redirect("xml_yukle")

        stok = get_object_or_404(StokKalemi, id=stok_id)
        yeni_miktar = stok.miktar + miktar

        stok.miktar_guncelle(
            yeni_miktar=yeni_miktar,
            tip="giris",
            kullanici=request.user if request.user.is_authenticated else None,
            aciklama=f"XML eşleştirme ile stok girişi - XML Ürün: {xml_urun_adi} / Barkod: {xml_barkod} / Fiyat: {fiyat}"
        )

        olusan_urun = stoktan_urun_olustur(stok)

    son_eslesmeyenler = request.session.get("son_eslesmeyenler", [])
    guncel_eslesmeyenler = []

    for item in son_eslesmeyenler:
        item_urun_adi = (item.get("urun_adi") or "").strip()
        item_barkod = (item.get("barkod") or "").strip()
        item_miktar = str(item.get("miktar") or "").strip()
        item_fiyat = str(item.get("fiyat") or "").strip()

        if (
            item_urun_adi == xml_urun_adi and
            item_barkod == xml_barkod and
            item_miktar == str(miktar) and
            item_fiyat == str(fiyat)
        ):
            continue

        guncel_eslesmeyenler.append(item)

    request.session["son_eslesmeyenler"] = guncel_eslesmeyenler
    request.session.modified = True

    if yeni_stok and olusan_urun:
        messages.success(
            request,
            f"{stok.ad} adlı yeni stok kartı açıldı, {miktar} {stok.birim} stok eklendi, "
            f"'{olusan_urun.ad}' ürünü oluşturuldu ve hızlı satışa eklendi."
        )
    elif yeni_stok:
        messages.success(
            request,
            f"{stok.ad} adlı yeni stok kartı açıldı ve {miktar} {stok.birim} stok eklendi."
        )
    elif olusan_urun:
        messages.success(
            request,
            f"{stok.ad} stoğuna {miktar} eklendi. '{olusan_urun.ad}' adlı ürün otomatik oluşturuldu / güncellendi."
        )
    else:
        messages.success(
            request,
            f"{stok.ad} stoğuna {miktar} eklendi."
        )

    stoklar = StokKalemi.objects.all().order_by("ad")

    return render(request, "adisyon_modulu/xml_yukle.html", {
        "stoklar": stoklar,
        "eslesmeyen": request.session.get("son_eslesmeyenler", []),
    })

def stoktan_urun_olustur(stok_kalemi):
    """
    Satılabilir ve otomatik ürün oluşturulacak stok kaleminden
    Urun kaydı oluşturur veya mevcut ürünü döndürür.
    """
    if not stok_kalemi:
        return None

    if not stok_kalemi.satilabilir_mi:
        return None

    if not stok_kalemi.otomatik_urun_olustur:
        return None

    mevcut_urun = Urun.objects.filter(stok_kalemi=stok_kalemi).first()
    if mevcut_urun:
        return mevcut_urun

    kategori, _ = Kategori.objects.get_or_create(
        ad="Hazır Ürünler",
        defaults={"sira": 999}
    )

    urun = Urun.objects.create(
        ad=stok_kalemi.ad,
        fiyat=stok_kalemi.fiyat or 0,
        kategori=kategori,
        stok_kalemi=stok_kalemi,
        aciklama=f"{stok_kalemi.ad} stok kaleminden otomatik oluşturuldu."
    )

    return urun

def urunu_hizli_satisa_ekle(urun, stok_kalemi):
    """
    Ürünü, ilgili şube için hızlı satış ürünlerine ekler.
    Mevcut kayıt varsa onu döndürür.
    """
    if not urun or not stok_kalemi:
        return None

    mevcut = HizliSatisUrun.objects.filter(
        urun=urun,
        sube=stok_kalemi.sube
    ).first()

    if mevcut:
        return mevcut

    hizli_satis_urun = HizliSatisUrun.objects.create(
        urun=urun,
        sube=stok_kalemi.sube,
        barkod=stok_kalemi.barkod or "",
        satis_fiyati=urun.fiyat or 0,
        stok_miktari=stok_kalemi.miktar or 0,
        aktif=True
    )

    return hizli_satis_urun

def receteden_stok_dus(siparis_item):
    """
    Reçeteli ürünlerde, sipariş adedi kadar bağlı stokları düşer.
    Aynı sipariş için ikinci kez çalışmaması için stok_dusuldu kontrolü yapar.
    """
    if not siparis_item:
        return False

    if siparis_item.stok_dusuldu:
        return False

    urun = siparis_item.urun
    if not urun:
        return False

    if not urun.receteli_mi:
        return False

    receteler = Recete.objects.filter(urun=urun).select_related("stok_item")
    if not receteler.exists():
        return False

    for recete in receteler:
        stok = recete.stok_item
        gerekli_miktar = recete.miktar * siparis_item.adet

        yeni_miktar = stok.miktar - gerekli_miktar

        stok.miktar_guncelle(
            yeni_miktar=yeni_miktar,
            tip="cikis",
            kullanici=None,
            siparis_item=siparis_item,
            aciklama=f"Reçeteden stok düşümü - Ürün: {urun.ad} / Adet: {siparis_item.adet}"
        )

    siparis_item.stok_dusuldu = True
    siparis_item.save(update_fields=["stok_dusuldu"])

    return True