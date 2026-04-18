# mutfak_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.db.models import Q
import time
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme

from ..models import Sube, Bolge, SiparisItem, Urun, Adisyon, Yazici, StokKalemi
from ..printing import yaziciya_veri_gonder
from .auth_views import mutfak_gorebilir_mi


def _safe_next_url(request, fallback_name):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return reverse(fallback_name)


@login_required
@user_passes_test(mutfak_gorebilir_mi)
def mutfak_ana_sayfa(request):
    return render(request, 'adisyon_modulu/mutfak_sube_secimi.html', {
        'subeler': Sube.objects.all(),
        'back_url': _safe_next_url(request, 'ana_sayfa'),
        'next_url': request.GET.get('next', ''),
    })


@login_required
@user_passes_test(mutfak_gorebilir_mi)
def mutfak_bolge_secimi(request, sube_id):
    s = get_object_or_404(Sube, id=sube_id)
    return render(request, 'adisyon_modulu/mutfak_bolge_secimi.html', {
        'sube': s,
        'bolgeler': s.bolgeler.all(),
        'back_url': _safe_next_url(request, 'mutfak_ana_sayfa'),
        'next_url': request.GET.get('next', ''),
    })


@login_required
@user_passes_test(mutfak_gorebilir_mi)
def mutfak_ekrani_filtreli(request, bolge_id):
    b = get_object_or_404(Bolge, id=bolge_id)
    s = SiparisItem.objects.filter(
        urun__bolge=b, 
        adisyon__durum='Acik', 
        hazir_mi=False
    ).order_by('adisyon__acilis_zamani')
    
    return render(request, 'adisyon_modulu/mutfak.html', {
        'bolge': b,
        'siparisler': s,
        'back_url': _safe_next_url(request, 'mutfak_ana_sayfa'),
        'next_url': request.GET.get('next', ''),
        'live_updates_enabled': getattr(settings, 'KITCHEN_LIVE_UPDATES_ENABLED', False),
    })


@login_required
@user_passes_test(mutfak_gorebilir_mi)
def siparis_hazir_isaretle(request, item_id):
    i = get_object_or_404(SiparisItem, id=item_id)
    if not i.hazir_mi:
        i.hazir_mi = True
        i.hazir_olma_zamani = timezone.now()
        i.save()
    next_url = request.GET.get('next')
    target_url = reverse('mutfak_ekrani_filtreli', kwargs={'bolge_id': i.urun.bolge.id})
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(f"{target_url}?next={next_url}")
    return redirect(target_url)


@login_required
def toplu_mutfak_yazdir(request, adisyon_id):
    a = get_object_or_404(Adisyon, id=adisyon_id)
    
    yazdirilacaklar = a.siparisler.filter(yazdirildi=False, iptal_edildi=False)
    
    if not yazdirilacaklar.exists():
        messages.warning(request, "Yazdırılacak sipariş bulunamadı.")
        return redirect('masa_detay', masa_id=a.masa.id) if a.masa else redirect('paket_detay', adisyon_id=a.id)
    
    # Stoktan düşüm yap ve hareketleri kaydet
    for item in yazdirilacaklar:
        for oge in item.urun.receteler.all():
            stok = StokKalemi.objects.filter(sube=a.sube, ad=oge.stok_item.ad).first()
            if stok:
                yeni_miktar = stok.miktar - (oge.miktar * item.adet)
                if hasattr(stok, 'miktar_guncelle'):
                    stok.miktar_guncelle(
                        yeni_miktar=yeni_miktar,
                        tip='cikis',
                        kullanici=request.user,
                        siparis_item=item,
                        aciklama=f"Masa {a.masa.masa_no} - {item.urun.ad} x{item.adet}"
                    )
                else:
                    stok.miktar = yeni_miktar
                    stok.save()
    
    try:
        yazici = Yazici.objects.filter(sube=a.sube).first()
        if not yazici:
            messages.error(request, "Bu şube için yazıcı tanımlanmamış!")
            return redirect('masa_detay', masa_id=a.masa.id) if a.masa else redirect('paket_detay', adisyon_id=a.id)
        
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
        komutlar.extend("MUTFAK SIPARIS".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(f"MASA: {a.masa.masa_no}".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(f"SAAT: {time.strftime('%H:%M')}".encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        
        # Sipariş listesi
        komutlar.extend(ESC + b'\x61' + b'\x00')
        komutlar.extend(("=" * 32).encode('utf-8'))
        komutlar.extend(b'\x0a')
        
        for item in yazdirilacaklar:
            urun_adi = turkce_duzelt(item.urun.ad)
            komutlar.extend(f"{urun_adi}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x11')
            komutlar.extend(f"ADET: {item.adet}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x00')
            
            if item.ikram_mi:
                komutlar.extend("(IKRAM)".encode('utf-8'))
                komutlar.extend(b'\x0a')
            
            komutlar.extend(("-" * 32).encode('utf-8'))
            komutlar.extend(b'\x0a')
        
        komutlar.extend(("=" * 32).encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        komutlar.extend(GS + b'\x56' + b'\x41' + b'\x00')
        
        yaziciya_veri_gonder(yazici, komutlar)
        
        yazdirilacaklar.update(yazdirildi=True)
        messages.success(request, f"✅ {yazdirilacaklar.count()} kalem sipariş yazdırıldı!")
        
    except Exception as e:
        messages.error(request, f"❌ Yazıcı hatası: {str(e)}")
        print(f"Yazıcı hatası: {e}")
    
    return redirect('masa_detay', masa_id=a.masa.id) if a.masa else redirect('paket_detay', adisyon_id=a.id)
