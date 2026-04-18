# views/api_views.py
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q 
from datetime import datetime
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import pytz

from ..models import (
    Sube, GarsonCagri, SiparisItem, Masa, Rezervasyon, Urun, Bolge
)
from ..printing import windows_yazicilari_listele

from ..models import StokKalemi  # Stok modelini de ekleyelim


def qr_menu(request, sube_id):
    sube = get_object_or_404(Sube, id=sube_id)
    urun_sorgu = Urun.objects.filter(bolge__sube=sube)
    from django.db.models import Prefetch
    from ..models import Kategori
    kategoriler = Kategori.objects.prefetch_related(Prefetch('urunler', queryset=urun_sorgu)).all()
    return render(request, 'adisyon_modulu/qr_menu.html', {
        'sube': sube,
        'kategoriler': kategoriler,
        'masa_no': (request.GET.get('masa') or '').strip(),
    })


def garson_cagir_api(request, sube_id):
    sube = get_object_or_404(Sube, id=sube_id)
    GarsonCagri.objects.create(sube=sube, masa_no=request.GET.get('masa', 'Bilinmiyor'))
    return JsonResponse({'status': 'ok'})


def yerel_yazici_api(request, sube_id):
    yazicilar = [{"ad": ad, "tip": "windows"} for ad in windows_yazicilari_listele()]
    return JsonResponse(yazicilar, safe=False)


@login_required
def bildirim_kontrol(request, sube_id):
    yeni_y = SiparisItem.objects.filter(hazir_mi=True, bildirim_gosterildi=False)
    if sube_id: 
        yeni_y = yeni_y.filter(
            Q(adisyon__masa__sube_id=sube_id) | Q(adisyon__sube_id=sube_id)
        )
    y_data = [{
        'tur': 'yemek', 
        'masa': i.adisyon.masa.masa_no if i.adisyon.masa else "PKT", 
        'urun': i.urun.ad
    } for i in yeni_y]
    yeni_y.update(bildirim_gosterildi=True)

    yeni_c = GarsonCagri.objects.filter(sube_id=sube_id, goruldu_mu=False)
    c_data = [{'tur': 'cagri', 'masa': i.masa_no} for i in yeni_c]
    yeni_c.update(goruldu_mu=True)

    return JsonResponse(y_data + c_data, safe=False)


def masa_uygunluk_kontrol(request):
    """AJAX ile masa uygunluğunu kontrol et"""
    if request.method == "GET":
        sube_id = request.GET.get('sube_id')
        tarih = request.GET.get('tarih')
        saat = request.GET.get('saat')
        kisi_sayisi = int(request.GET.get('kisi_sayisi', 1))
        
        if not all([sube_id, tarih, saat]):
            return JsonResponse({'error': 'Eksik parametre'}, status=400)
        
        from django.utils import timezone
        from datetime import datetime
        import pytz
        
        turkey_tz = pytz.timezone('Europe/Istanbul')
        secilen_zaman = datetime.strptime(f"{tarih} {saat}", "%Y-%m-%d %H:%M")
        secilen_zaman = turkey_tz.localize(secilen_zaman)
        
        simdi = timezone.localtime(timezone.now())
        sube = get_object_or_404(Sube, id=sube_id)
        
        masalar = sube.masalar.filter(kapasite__gte=kisi_sayisi)
        uygun_masalar = []
        
        for masa in masalar:
            kilitli_rezervasyon = Rezervasyon.objects.filter(
                masa=masa,
                tarih=tarih,
                masa_kilitli=True,
                durum__in=['Onaylandı', 'Bekliyor']
            ).first()
            
            if kilitli_rezervasyon:
                if kilitli_rezervasyon.kilit_baslangic and kilitli_rezervasyon.kilit_bitis:
                    if kilitli_rezervasyon.kilit_baslangic <= simdi <= kilitli_rezervasyon.kilit_bitis:
                        continue
                    
                    if (secilen_zaman >= kilitli_rezervasyon.kilit_baslangic and 
                        secilen_zaman <= kilitli_rezervasyon.kilit_bitis):
                        continue
                    
                    uygun_masalar.append({
                        'id': masa.id,
                        'no': masa.masa_no,
                        'kapasite': masa.kapasite,
                        'kilit_bilgi': f"⚠️ {kilitli_rezervasyon.kilit_baslangic.strftime('%H:%M')} - {kilitli_rezervasyon.kilit_bitis.strftime('%H:%M')} arası dolu"
                    })
                else:
                    uygun_masalar.append({
                        'id': masa.id,
                        'no': masa.masa_no,
                        'kapasite': masa.kapasite
                    })
            else:
                uygun_masalar.append({
                    'id': masa.id,
                    'no': masa.masa_no,
                    'kapasite': masa.kapasite
                })
        
        return JsonResponse(uygun_masalar, safe=False)
    
    return JsonResponse({'error': 'Geçersiz istek'}, status=400)


@login_required
def masa_kilit_kontrol_api(request):
    """API - Belirli bir masanın kilit durumunu kontrol et"""
    if request.method == "GET":
        masa_id = request.GET.get('masa_id')
        tarih = request.GET.get('tarih')
        saat = request.GET.get('saat')
        
        if not all([masa_id, tarih, saat]):
            return JsonResponse({'error': 'Eksik parametre'}, status=400)
        
        from django.utils import timezone
        from datetime import datetime
        import pytz
        
        masa = get_object_or_404(Masa, id=masa_id)
        
        turkey_tz = pytz.timezone('Europe/Istanbul')
        secilen_zaman = datetime.strptime(f"{tarih} {saat}", "%Y-%m-%d %H:%M")
        secilen_zaman = turkey_tz.localize(secilen_zaman)
        
        simdi = timezone.localtime(timezone.now())
        
        kilitli_rezervasyon = Rezervasyon.objects.filter(
            masa=masa,
            tarih=tarih,
            masa_kilitli=True,
            durum__in=['Onaylandı', 'Bekliyor']
        ).first()
        
        if kilitli_rezervasyon and kilitli_rezervasyon.kilit_baslangic and kilitli_rezervasyon.kilit_bitis:
            if kilitli_rezervasyon.kilit_baslangic <= simdi <= kilitli_rezervasyon.kilit_bitis:
                return JsonResponse({
                    'kilitli': True,
                    'aktif': True,
                    'rezervasyon_id': kilitli_rezervasyon.id,
                    'musteri': kilitli_rezervasyon.musteri_adi,
                    'kilit_baslangic': timezone.localtime(kilitli_rezervasyon.kilit_baslangic).strftime("%H:%M"),
                    'kilit_bitis': timezone.localtime(kilitli_rezervasyon.kilit_bitis).strftime("%H:%M"),
                    'mesaj': f"🔒 Masa {kilitli_rezervasyon.kilit_baslangic.strftime('%H:%M')} - {kilitli_rezervasyon.kilit_bitis.strftime('%H:%M')} arası {kilitli_rezervasyon.musteri_adi} için kilitli"
                })
            
            elif secilen_zaman >= kilitli_rezervasyon.kilit_baslangic and secilen_zaman <= kilitli_rezervasyon.kilit_bitis:
                return JsonResponse({
                    'kilitli': True,
                    'aktif': False,
                    'rezervasyon_id': kilitli_rezervasyon.id,
                    'musteri': kilitli_rezervasyon.musteri_adi,
                    'kilit_baslangic': timezone.localtime(kilitli_rezervasyon.kilit_baslangic).strftime("%H:%M"),
                    'kilit_bitis': timezone.localtime(kilitli_rezervasyon.kilit_bitis).strftime("%H:%M"),
                    'mesaj': f"⚠️ Masa {kilitli_rezervasyon.kilit_baslangic.strftime('%H:%M')} - {kilitli_rezervasyon.kilit_bitis.strftime('%H:%M')} arası dolu"
                })
        
        return JsonResponse({
            'kilitli': False,
            'mesaj': '✅ Masa uygun'
        })
    
    return JsonResponse({'error': 'Geçersiz istek'}, status=400)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_urun_sira_kaydet(request):
    try:
        data = json.loads(request.body)
        sira_data = data.get('sira_data', [])
        for item in sira_data:
            urun_id = item.get('id')
            yeni_sira = item.get('sira')
            kategori_id = item.get('kategori_id')
            
            urun = Urun.objects.filter(id=urun_id).first()
            if urun:
                urun.sira = yeni_sira
                update_fields = ['sira']
                
                if kategori_id is not None:
                    urun.kategori_id = None if str(kategori_id) == 'none' else kategori_id
                    update_fields.append('kategori_id')
                    
                urun.save(update_fields=update_fields)
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
