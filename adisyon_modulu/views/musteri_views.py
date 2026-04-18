# views/musteri_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta

from ..models import Musteri, Adisyon, IndirimKuponu, KuponKullanim


@login_required
def musteri_profil(request, musteri_id):
    """Müşteri profil sayfası"""
    musteri = get_object_or_404(Musteri, id=musteri_id)
    
    # Müşterinin sipariş geçmişi
    siparisler = Adisyon.objects.filter(
        musteri=musteri,
        durum='Kapali'
    ).order_by('-acilis_zamani')[:20]
    
    # Müşteriye özel aktif kuponlar
    bugun = timezone.now().date()
    kuponlar = IndirimKuponu.objects.filter(
        durum='aktif',
        baslangic_tarihi__lte=bugun,
        bitis_tarihi__gte=bugun
    ).filter(
        Q(uygun_seviyeler__icontains=musteri.sadakat_seviyesi) | Q(uygun_seviyeler__isnull=True)
    )[:10]
    
    # Puan hareketleri (StokHareket benzeri bir model kullanılabilir)
    # Şimdilik boş liste gönderiyoruz, ileride ekleyebiliriz
    puan_hareketleri = []
    
    context = {
        'musteri': musteri,
        'siparisler': siparisler,
        'kuponlar': kuponlar,
        'puan_hareketleri': puan_hareketleri,
    }
    return render(request, 'adisyon_modulu/musteri_profil.html', context)


@login_required
def musteri_ara(request):
    """Müşteri arama sayfası"""
    query = request.GET.get('q', '')
    musteriler = []
    
    if query:
        musteriler = Musteri.objects.filter(
            Q(telefon__icontains=query) | 
            Q(ad_soyad__icontains=query) |
            Q(email__icontains=query)
        )[:20]
    
    context = {
        'query': query,
        'musteriler': musteriler,
    }
    return render(request, 'adisyon_modulu/musteri_ara.html', context)


@login_required
def musteri_ekle(request):
    """Yeni müşteri ekle"""
    if request.method == "POST":
        # Aynı telefon numarası var mı kontrol et
        telefon = request.POST.get('telefon')
        if Musteri.objects.filter(telefon=telefon).exists():
            messages.error(request, f"{telefon} numarası zaten kayıtlı!")
            return redirect('musteri_ekle')
        
        # Yeni müşteri oluştur
        musteri = Musteri.objects.create(
            ad_soyad=request.POST.get('ad_soyad'),
            telefon=telefon,
            adres=request.POST.get('adres', ''),
            email=request.POST.get('email', ''),
            dogum_tarihi=request.POST.get('dogum_tarihi') or None,
            cinsiyet=request.POST.get('cinsiyet') or None,
            sadakat_puani=0,
            toplam_harcama=0,
            ziyaret_sayisi=0,
            sadakat_seviyesi='Bronz'
        )
        
        messages.success(request, f"{musteri.ad_soyad} başarıyla eklendi!")
        return redirect('musteri_profil', musteri_id=musteri.id)
    
    return render(request, 'adisyon_modulu/musteri_ekle.html')


@login_required
def kupon_kullan(request, kupon_id, adisyon_id):
    """Kuponu adisyonda kullan"""
    kupon = get_object_or_404(IndirimKuponu, id=kupon_id, durum='aktif')
    adisyon = get_object_or_404(Adisyon, id=adisyon_id, durum='Acik')
    
    if not adisyon.musteri:
        messages.error(request, "Bu adisyona ait müşteri bulunamadı!")
        return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)
    
    basarili, mesaj = kupon.kullan(adisyon.musteri, adisyon)
    
    if basarili:
        # Kupon kullanım kaydı oluştur
        KuponKullanim.objects.create(
            kupon=kupon,
            musteri=adisyon.musteri,
            adisyon=adisyon,
            indirim_tutari=adisyon.indirim_tutari
        )
        messages.success(request, mesaj)
    else:
        messages.error(request, mesaj)
    
    return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)


@login_required
def musteri_puan_goruntule(request, musteri_id):
    """Müşteri puanını görüntüle (AJAX için)"""
    musteri = get_object_or_404(Musteri, id=musteri_id)
    
    from django.http import JsonResponse
    return JsonResponse({
        'ad_soyad': musteri.ad_soyad,
        'sadakat_puani': musteri.sadakat_puani,
        'sadakat_seviyesi': musteri.sadakat_seviyesi,
        'dogum_gunu_indirimi': musteri.dogum_gunu_indirimi(),
    })# views/musteri_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.utils import timezone
from datetime import datetime, timedelta

from ..models import Musteri, Adisyon, IndirimKuponu, KuponKullanim


@login_required
def musteri_profil(request, musteri_id):
    """Müşteri profil sayfası"""
    musteri = get_object_or_404(Musteri, id=musteri_id)
    
    # Müşterinin sipariş geçmişi
    siparisler = Adisyon.objects.filter(
        musteri=musteri,
        durum='Kapali'
    ).order_by('-acilis_zamani')[:20]
    
    # Müşteriye özel aktif kuponlar
    bugun = timezone.now().date()
    kuponlar = IndirimKuponu.objects.filter(
        durum='aktif',
        baslangic_tarihi__lte=bugun,
        bitis_tarihi__gte=bugun
    ).filter(
        Q(uygun_seviyeler__icontains=musteri.sadakat_seviyesi) | Q(uygun_seviyeler__isnull=True)
    )[:10]
    
    # Puan hareketleri (StokHareket benzeri bir model kullanılabilir)
    # Şimdilik boş liste gönderiyoruz, ileride ekleyebiliriz
    puan_hareketleri = []
    
    context = {
        'musteri': musteri,
        'siparisler': siparisler,
        'kuponlar': kuponlar,
        'puan_hareketleri': puan_hareketleri,
    }
    return render(request, 'adisyon_modulu/musteri_profil.html', context)


@login_required
def musteri_ara(request):
    """Müşteri arama sayfası"""
    query = request.GET.get('q', '')
    musteriler = []
    
    if query:
        musteriler = Musteri.objects.filter(
            Q(telefon__icontains=query) | 
            Q(ad_soyad__icontains=query) |
            Q(email__icontains=query)
        )[:20]
    
    context = {
        'query': query,
        'musteriler': musteriler,
    }
    return render(request, 'adisyon_modulu/musteri_ara.html', context)


@login_required
def musteri_ekle(request):
    """Yeni müşteri ekle"""
    if request.method == "POST":
        # Aynı telefon numarası var mı kontrol et
        telefon = request.POST.get('telefon')
        if Musteri.objects.filter(telefon=telefon).exists():
            messages.error(request, f"{telefon} numarası zaten kayıtlı!")
            return redirect('musteri_ekle')
        
        # Yeni müşteri oluştur
        musteri = Musteri.objects.create(
            ad_soyad=request.POST.get('ad_soyad'),
            telefon=telefon,
            adres=request.POST.get('adres', ''),
            email=request.POST.get('email', ''),
            dogum_tarihi=request.POST.get('dogum_tarihi') or None,
            cinsiyet=request.POST.get('cinsiyet') or None,
            sadakat_puani=0,
            toplam_harcama=0,
            ziyaret_sayisi=0,
            sadakat_seviyesi='Bronz'
        )
        
        messages.success(request, f"{musteri.ad_soyad} başarıyla eklendi!")
        return redirect('musteri_profil', musteri_id=musteri.id)
    
    return render(request, 'adisyon_modulu/musteri_ekle.html')


@login_required
def kupon_kullan(request, kupon_id, adisyon_id):
    """Kuponu adisyonda kullan"""
    kupon = get_object_or_404(IndirimKuponu, id=kupon_id, durum='aktif')
    adisyon = get_object_or_404(Adisyon, id=adisyon_id, durum='Acik')
    
    if not adisyon.musteri:
        messages.error(request, "Bu adisyona ait müşteri bulunamadı!")
        return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)
    
    basarili, mesaj = kupon.kullan(adisyon.musteri, adisyon)
    
    if basarili:
        # Kupon kullanım kaydı oluştur
        KuponKullanim.objects.create(
            kupon=kupon,
            musteri=adisyon.musteri,
            adisyon=adisyon,
            indirim_tutari=adisyon.indirim_tutari
        )
        messages.success(request, mesaj)
    else:
        messages.error(request, mesaj)
    
    return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)


@login_required
def musteri_puan_goruntule(request, musteri_id):
    """Müşteri puanını görüntüle (AJAX için)"""
    musteri = get_object_or_404(Musteri, id=musteri_id)
    
    from django.http import JsonResponse
    return JsonResponse({
        'ad_soyad': musteri.ad_soyad,
        'sadakat_puani': musteri.sadakat_puani,
        'sadakat_seviyesi': musteri.sadakat_seviyesi,
        'dogum_gunu_indirimi': musteri.dogum_gunu_indirimi(),
    })

@login_required
def kisisel_indirim_uygula(request, indirim_id, adisyon_id):
    """Kişisel indirimi adisyona uygula"""
    from ..models import KisiselIndirim, Adisyon
    
    indirim = get_object_or_404(KisiselIndirim, id=indirim_id, aktif=True)
    adisyon = get_object_or_404(Adisyon, id=adisyon_id, durum='Acik')
    
    # İndirim bu müşteriye ait mi kontrol et
    if indirim.musteri.id != adisyon.musteri.id:
        messages.error(request, "Bu indirim bu müşteriye ait değil!")
        return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)
    
    # İndirimi uygula
    basarili, mesaj = indirim.indirim_uygula(adisyon)
    
    if basarili:
        messages.success(request, f"✅ {mesaj}")
    else:
        messages.error(request, f"❌ {mesaj}")
    
    return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)