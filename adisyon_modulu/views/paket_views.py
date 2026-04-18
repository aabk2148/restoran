# views/paket_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test  # BU ÖNEMLİ!
from django.contrib import messages
from django.db.models import Q, Prefetch
import time

from ..models import (
    Sube, Musteri, Adisyon, Urun, Kategori, 
    SiparisItem, Yazici
)
from ..printing import yaziciya_veri_gonder
from .auth_views import siparis_girebilir_mi


@login_required
def paket_servis_ana(request, sube_id):
    sube = get_object_or_404(Sube, id=sube_id)
    query = request.GET.get('q', '')
    musteriler = Musteri.objects.filter(
        Q(telefon__icontains=query) | Q(ad_soyad__icontains=query)
    ) if query else []
    paketler = Adisyon.objects.filter(
        sube=sube, 
        siparis_turu='Paket', 
        durum='Acik'
    ).order_by('-acilis_zamani')
    
    return render(request, 'adisyon_modulu/paket_servis.html', {
        'sube': sube, 
        'musteriler': musteriler, 
        'query': query, 
        'paketler': paketler
    })


@login_required
def musteri_ekle(request, sube_id):
    if request.method == "POST":
        m = Musteri.objects.create(
            ad_soyad=request.POST.get('ad_soyad'),
            telefon=request.POST.get('telefon'),
            adres=request.POST.get('adres')
        )
        return redirect(f'/paket-servis/{sube_id}/?q={m.telefon}')
    
    return render(request, 'adisyon_modulu/musteri_ekle.html', {'sube_id': sube_id})


@login_required
def paket_siparis_olustur(request, sube_id, musteri_id):
    sube = get_object_or_404(Sube, id=sube_id)
    m = get_object_or_404(Musteri, id=musteri_id)
    a = Adisyon.objects.create(
        sube=sube, 
        musteri=m, 
        siparis_turu='Paket', 
        paket_durumu='Hazirlaniyor', 
        durum='Acik'
    )
    return redirect('paket_detay', adisyon_id=a.id)


@login_required
def paket_detay(request, adisyon_id):
    a = get_object_or_404(Adisyon, id=adisyon_id)
    urun_sorgu = Urun.objects.filter(bolge__sube=a.sube)
    k = Kategori.objects.prefetch_related(Prefetch('urunler', queryset=urun_sorgu)).all()
    
    yazdirilabilir = a.siparisler.filter(yazdirildi=False).exists()
    
    context = {
        'adisyon': a, 
        'kategoriler': k,
        'yazdirilabilir': yazdirilabilir
    }
    return render(request, 'adisyon_modulu/paket_detay.html', context)


@login_required
def paket_siparis_ekle(request, adisyon_id):
    if request.method == "POST":
        a = get_object_or_404(Adisyon, id=adisyon_id)
        u = get_object_or_404(Urun, id=request.POST.get('urun_id'))
        SiparisItem.objects.create(adisyon=a, urun=u, adet=1)
    
    return redirect('paket_detay', adisyon_id=adisyon_id)


@login_required
def paket_durum_degistir(request, adisyon_id):
    a = get_object_or_404(Adisyon, id=adisyon_id)
    d = request.GET.get('durum')
    if d in ['Hazirlaniyor', 'Yolda', 'Teslim Edildi']:
        a.paket_durumu = d
        a.save()
    
    return redirect('paket_detay', adisyon_id=a.id)


@login_required
def paket_fis_yazdir(request, adisyon_id):
    """Paket servis fişini yazdır"""
    a = get_object_or_404(Adisyon, id=adisyon_id)
    
    try:
        yazici = Yazici.objects.filter(sube=a.sube, yazici_tipi='kasa').first()
        if not yazici:
            yazici = Yazici.objects.filter(sube=a.sube).first()
            if not yazici:
                messages.error(request, "Bu şube için yazıcı tanımlanmamış!")
                return redirect('paket_detay', adisyon_id=a.id)
        
        # Türkçe karakter düzeltme fonksiyonu
        def turkce_duzelt(metin):
            donusum = {
                'ı': 'i', 'İ': 'I', 'ğ': 'g', 'Ğ': 'G',
                'ü': 'u', 'Ü': 'U', 'ş': 's', 'Ş': 'S',
                'ö': 'o', 'Ö': 'O', 'ç': 'c', 'Ç': 'C',
            }
            for turkce, ascii_ in donusum.items():
                metin = metin.replace(turkce, ascii_)
            return metin
        
        ESC = b'\x1b'
        GS = b'\x1d'
        
        komutlar = bytearray()
        komutlar.extend(ESC + b'\x40')  # Reset
        
        # Başlık
        komutlar.extend(ESC + b'\x61' + b'\x01')
        komutlar.extend(ESC + b'\x21' + b'\x30')
        komutlar.extend("LAR".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(ESC + b'\x21' + b'\x00')
        komutlar.extend("PAKET SERVIS".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(turkce_duzelt(f"Sube: {a.sube.ad}").encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(f"Siparis No: {a.id}".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(f"Tarih: {time.strftime('%d.%m.%Y %H:%M')}".encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        
        # Müşteri Bilgileri
        if a.musteri:
            komutlar.extend(ESC + b'\x45' + b'\x01')
            komutlar.extend("MUSTERI BILGILERI".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x45' + b'\x00')
            komutlar.extend(f"Ad: {turkce_duzelt(a.musteri.ad_soyad)}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(f"Tel: {a.musteri.telefon}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            if a.musteri.adres:
                komutlar.extend(f"Adres: {turkce_duzelt(a.musteri.adres)}".encode('utf-8'))
                komutlar.extend(b'\x0a')
            komutlar.extend(b'\x0a')
        
        # Siparişler
        komutlar.extend(ESC + b'\x61' + b'\x00')
        komutlar.extend(("=" * 32).encode('utf-8'))
        komutlar.extend(b'\x0a')
        
        for item in a.siparisler.all():
            urun_adi = turkce_duzelt(item.urun.ad)
            komutlar.extend(f"{urun_adi}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x11')
            komutlar.extend(f"  {item.adet} x {float(item.urun.fiyat):.2f}TL".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x00')
            
            if item.ikram_mi:
                komutlar.extend("  (IKRAM)".encode('utf-8'))
                komutlar.extend(b'\x0a')
            
            komutlar.extend(("-" * 32).encode('utf-8'))
            komutlar.extend(b'\x0a')
        
        # Toplam
        komutlar.extend(("=" * 32).encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(f"ARA TOPLAM: {float(a.ara_toplam()):.2f}TL".encode('utf-8'))
        komutlar.extend(b'\x0a')
        if a.indirim_tutari > 0:
            komutlar.extend(f"INDIRIM: -{float(a.indirim_tutari):.2f}TL".encode('utf-8'))
            komutlar.extend(b'\x0a')
        komutlar.extend(ESC + b'\x21' + b'\x11')
        komutlar.extend(f"TOPLAM: {float(a.toplam_tutar()):.2f}TL".encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        komutlar.extend(ESC + b'\x21' + b'\x00')
        
        komutlar.extend(f"Durum: {a.get_paket_durumu_display()}".encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        komutlar.extend("TESEKKUR EDERIZ".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend("Bizi tercih ettiginiz icin".encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        komutlar.extend(GS + b'\x56' + b'\x41' + b'\x00')
        
        yaziciya_veri_gonder(yazici, komutlar)
        
        messages.success(request, "✅ Paket servis fişi yazdırıldı!")
        
    except Exception as e:
        messages.error(request, f"❌ Yazıcı hatası: {str(e)}")
        print(f"Yazıcı hatası: {e}")
    
    return redirect('paket_detay', adisyon_id=a.id)
