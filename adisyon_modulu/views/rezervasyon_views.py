# views/rezervasyon_views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required  # SADECE login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
import pytz

from ..models import (
    Sube, Musteri, Rezervasyon, Masa
)


@login_required
def rezervasyon_listesi(request):
    """Tüm rezervasyonları listele"""
    sube_id = request.GET.get('sube')
    tarih = request.GET.get('tarih', timezone.now().date())
    durum = request.GET.get('durum', '')
    
    rezervasyonlar = Rezervasyon.objects.filter(tarih=tarih)
    
    if sube_id:
        rezervasyonlar = rezervasyonlar.filter(sube_id=sube_id)
    
    if durum:
        rezervasyonlar = rezervasyonlar.filter(durum=durum)
    
    toplam = rezervasyonlar.count()
    onayli = rezervasyonlar.filter(durum='Onaylandı').count()
    bekleyen = rezervasyonlar.filter(durum='Bekliyor').count()
    
    context = {
        'rezervasyonlar': rezervasyonlar,
        'tarih': tarih,
        'subeler': Sube.objects.all(),
        'secili_sube': sube_id,
        'secili_durum': durum,
        'toplam': toplam,
        'onayli': onayli,
        'bekleyen': bekleyen,
    }
    return render(request, 'adisyon_modulu/rezervasyon_listesi.html', context)


@login_required
def rezervasyon_ekle(request, sube_id=None):
    """Yeni rezervasyon oluştur"""
    print(">>>>>>>>>> REZERVASYON_EKLE FONKSİYONU ÇAĞRILDI <<<<<<<<<<")
    print(f"Request method: {request.method}")
    print(f"sube_id: {sube_id}")
    
    if request.method == "POST":
        sube = get_object_or_404(Sube, id=request.POST.get('sube_id'))
        telefon = request.POST.get('telefon')
        
        tarih_str = request.POST.get('tarih')
        saat_str = request.POST.get('saat')
        
        print("\n" + "="*60)
        print("YENİ REZERVASYON İSTEĞİ - BAŞLANGIÇ")
        print("="*60)
        print(f"Şube: {sube.ad}")
        print(f"Müşteri: {request.POST.get('musteri_adi')}")
        print(f"Telefon: {telefon}")
        print(f"Tarih: {tarih_str}")
        print(f"Saat: {saat_str}")
        print(f"Kişi: {request.POST.get('kisi_sayisi')}")
        print(f"Masa ID: {request.POST.get('masa_id')}")
        print(f"Request method: {request.method}")
        print(f"POST verileri: {dict(request.POST)}")
        
        musteri = None
        if telefon:
            musteri = Musteri.objects.filter(telefon=telefon).first()
            if musteri:
                print(f"Mevcut müşteri bulundu: {musteri.ad_soyad} (ID: {musteri.id})")
        
        rezervasyon = Rezervasyon.objects.create(
            sube=sube,
            musteri=musteri,
            musteri_adi=request.POST.get('musteri_adi'),
            musteri_telefon=telefon,
            musteri_email=request.POST.get('email', ''),
            kisi_sayisi=request.POST.get('kisi_sayisi'),
            tarih=tarih_str,
            saat=saat_str,
            ozel_istek=request.POST.get('ozel_istek', ''),
            durum='Bekliyor',
            olusturan=request.user,
            masa_kilitli=False
        )

        print(f"Rezervasyon oluşturuldu ID: {rezervasyon.id}")
        print(f"Rezervasyon.masa başlangıç: {rezervasyon.masa}")
        
        masa_id = request.POST.get('masa_id')
        if masa_id and masa_id.strip():
            print(f"Masa ID alındı: {masa_id}")
            masa = get_object_or_404(Masa, id=masa_id, sube=sube)
            print(f"Masa bulundu: {masa.masa_no} (ID: {masa.id})")
            
            rezervasyon.masa = masa
            rezervasyon.save()
            print(f"Masa atandı, rezervasyon.masa artık: {rezervasyon.masa}")

            print("masa_kilit() çağrılıyor...")
            
            try:
                basarili, mesaj = rezervasyon.masa_kilit()
                print(f"masa_kilit() sonucu: {basarili} - {mesaj}")
                
                if basarili:
                    rezervasyon.durum = 'Onaylandı'
                    rezervasyon.save()
                    print(f"Rezervasyon onaylandı, masa_kilitli: {rezervasyon.masa_kilitli}")
                    messages.success(request, f"Masa {masa.masa_no} atandı! {mesaj}")
                else:
                    print(f"Masa kilitlenemedi: {mesaj}")
                    messages.warning(request, f"Masa atanamadı: {mesaj}")
            except Exception as e:
                print(f"HATA: {str(e)}")
                import traceback
                traceback.print_exc()
                messages.error(request, f"Hata: {str(e)}")
        else:
            print("Masa seçilmedi veya masa_id boş")
            print(f"masa_id değeri: '{masa_id}'")
            messages.info(request, "Rezervasyon oluşturuldu, masa atanmadı.")
        
        print("="*60 + "\n")
        return redirect('rezervasyon_detay', rezervasyon_id=rezervasyon.id)
    
    # GET isteği - formu göster
    import datetime
    
    subeler = Sube.objects.all()
    secili_sube = None
    masalar = []
    
    if sube_id:
        secili_sube = get_object_or_404(Sube, id=sube_id)
    
    simdi = timezone.localtime(timezone.now())
    bugun = simdi.date()
    bir_sonraki_saat = (simdi + datetime.timedelta(hours=1)).replace(minute=0, second=0, microsecond=0).strftime('%H:%M')
    
    context = {
        'subeler': subeler,
        'secili_sube': secili_sube,
        'masalar': masalar,
        'bugun': bugun.strftime('%Y-%m-%d'),
        'bir_sonraki_saat': bir_sonraki_saat,
    }
    return render(request, 'adisyon_modulu/rezervasyon_ekle.html', context)


@login_required
def rezervasyon_detay(request, rezervasyon_id):
    """Rezervasyon detayını göster"""
    rezervasyon = get_object_or_404(Rezervasyon, id=rezervasyon_id)
    
    benzer_rezervasyonlar = Rezervasyon.objects.filter(
        tarih=rezervasyon.tarih,
        sube=rezervasyon.sube
    ).exclude(id=rezervasyon.id)[:5]
    
    context = {
        'rezervasyon': rezervasyon,
        'benzer_rezervasyonlar': benzer_rezervasyonlar,
    }
    return render(request, 'adisyon_modulu/rezervasyon_detay.html', context)


@login_required
def rezervasyon_onay(request, rezervasyon_id):
    """Rezervasyonu onayla ve masa ata"""
    rezervasyon = get_object_or_404(Rezervasyon, id=rezervasyon_id)
    
    if request.method == "POST":
        masa_id = request.POST.get('masa_id')
        if masa_id:
            masa = get_object_or_404(Masa, id=masa_id, sube=rezervasyon.sube)
            rezervasyon.masa = masa
            rezervasyon.durum = 'Onaylandı'
            rezervasyon.save()
            messages.success(request, f"Rezervasyon onaylandı ve Masa {masa.masa_no} atandı.")
        else:
            messages.error(request, "Lütfen bir masa seçin!")
    
    return redirect('rezervasyon_detay', rezervasyon_id=rezervasyon.id)


@login_required
def rezervasyon_iptal(request, rezervasyon_id):
    """Rezervasyonu iptal et"""
    rezervasyon = get_object_or_404(Rezervasyon, id=rezervasyon_id)
    
    if request.method == "POST":
        iptal_nedeni = request.POST.get('iptal_nedeni', '')
        rezervasyon.durum = 'İptal Edildi'
        rezervasyon.musteri_notu = (rezervasyon.musteri_notu or '') + f"\nİPTAL: {iptal_nedeni}"
        rezervasyon.save()
        messages.success(request, "Rezervasyon iptal edildi.")
    
    return redirect('rezervasyon_detay', rezervasyon_id=rezervasyon.id)


@login_required
def rezervasyon_gelmedi(request, rezervasyon_id):
    """Rezervasyonu gelmedi olarak işaretle"""
    rezervasyon = get_object_or_404(Rezervasyon, id=rezervasyon_id)
    rezervasyon.durum = 'Gelmedi'
    rezervasyon.masa_kilitli = False
    rezervasyon.save()
    messages.warning(request, "Müşteri gelmedi olarak işaretlendi ve masa kilidi (varsa) kaldırıldı.")
    return redirect('rezervasyon_detay', rezervasyon_id=rezervasyon.id)


@login_required
def rezervasyon_tamamla(request, rezervasyon_id):
    """Rezervasyonu tamamlandı olarak işaretle"""
    rezervasyon = get_object_or_404(Rezervasyon, id=rezervasyon_id)
    rezervasyon.durum = 'Tamamlandı'
    rezervasyon.save()
    messages.success(request, "Rezervasyon tamamlandı olarak işaretlendi.")
    return redirect('rezervasyon_detay', rezervasyon_id=rezervasyon.id)


@login_required
def rezervasyon_masa_ata(request, rezervasyon_id):
    """Rezervasyona masa ata ve kilitle"""
    rezervasyon = get_object_or_404(Rezervasyon, id=rezervasyon_id)
    
    if request.method == "POST":
        masa_id = request.POST.get('masa_id')
        if not masa_id:
            messages.error(request, "Lütfen bir masa seçin!")
            return redirect('rezervasyon_detay', rezervasyon_id=rezervasyon.id)
        
        masa = get_object_or_404(Masa, id=masa_id, sube=rezervasyon.sube)
        rezervasyon.masa = masa
        basarili, mesaj = rezervasyon.masa_kilit()
        
        if basarili:
            rezervasyon.durum = 'Onaylandı'
            rezervasyon.save()
            messages.success(request, f"Masa {masa.masa_no} başarıyla atandı ve kiralandı!")
        else:
            messages.error(request, f"Masa atanamadı: {mesaj}")
    
    return redirect('rezervasyon_detay', rezervasyon_id=rezervasyon.id)


@login_required
def rezervasyon_otomatik_kontrol(request):
    """Her saat başı çalışacak fonksiyon - zamanı geçen rezervasyonları temizle"""
    
    gecmis_kilitler = Rezervasyon.objects.filter(
        masa_kilitli=True,
        kilit_bitis__lt=timezone.now()
    )
    
    for rez in gecmis_kilitler:
        rez.masa_kilitli = False
        rez.save()
        print(f"{rez.id} numaralı rezervasyonun masa kilidi kalktı")
    
    yakin_zaman = timezone.now() + timedelta(minutes=30)
    yaklasanlar = Rezervasyon.objects.filter(
        tarih=timezone.now().date(),
        saat__gte=timezone.now().time(),
        saat__lte=yakin_zaman.time(),
        durum='Onaylandı',
        hatirlatma_yapildi=False
    )
    
    for rez in yaklasanlar:
        rez.hatirlatma_yapildi = True
        rez.save()
        print(f"{rez.musteri_adi} için hatırlatma yapıldı")
    
    return JsonResponse({
        'kilidi_kalkan': gecmis_kilitler.count(),
        'hatirlatma_yapilan': yaklasanlar.count()
    })