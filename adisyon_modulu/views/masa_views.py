from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.urls import reverse
from django.db.models import Prefetch, F, Sum
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.http import JsonResponse
import time
import logging
from types import SimpleNamespace

from ..models import (
    Sube, Yazici, Kategori, Urun, Masa, Adisyon, GarsonCagri,
    SiparisItem, StokKalemi, IptalKaydi, Musteri, MenuSiparisTalebi,
    KisiselIndirim
)
from .auth_views import siparis_girebilir_mi
from .stok_views import receteden_stok_dus
from ..printing import yaziciya_veri_gonder
import json
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse


logger = logging.getLogger(__name__)


def _safe_next_url(request, fallback_name):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return reverse(fallback_name)


def _ilk_kurulum_masa_duzenini_olustur(sube):
    masalar = list(sube.masalar.all().order_by('id'))
    if len(masalar) <= 1:
        return

    if any(masa.pos_x != 0 or masa.pos_y != 0 for masa in masalar):
        return

    for masa in masalar:
        masa.pos_x, masa.pos_y = masa._varsayilan_konum_hesapla()

    Masa.objects.bulk_update(masalar, ['pos_x', 'pos_y'])


@login_required
def sube_detay(request, sube_id):
    start_total = time.time()

    sube = get_object_or_404(Sube, id=sube_id)
    _ilk_kurulum_masa_duzenini_olustur(sube)
    bugun = timezone.now().date()

    masalar = (
        sube.masalar.all()
        .order_by('masa_no', 'id')
        .prefetch_related(
            Prefetch(
                'rezervasyon_set',
                queryset=sube.rezervasyonlar.filter(
                    tarih=bugun,
                    durum__in=['Onaylandı', 'Bekliyor']
                ).order_by('saat')
            )
        )
    )

    t1 = time.time()
    print(f"sube_detay -> masalar hazirlanma: {t1 - start_total:.3f} sn")

    paketler = (
        Adisyon.objects
        .filter(sube=sube, siparis_turu='Paket', durum='Acik')
        .select_related('sube', 'musteri', 'garson')
        .order_by('-acilis_zamani')
    )

    t2 = time.time()
    print(f"sube_detay -> paketler: {t2 - t1:.3f} sn")

    kritik_stoklar = (
        StokKalemi.objects
        .filter(sube=sube, miktar__lte=F('kritik_seviye'))
        .select_related('sube')
    )

    bekleyen_menu_talepleri = (
        MenuSiparisTalebi.objects
        .filter(sube=sube, durum='Beklemede')
        .prefetch_related('kalemler')
        .order_by('-olusturma_zamani')
    )

    t3 = time.time()
    print(f"sube_detay -> kritik_stoklar: {t3 - t2:.3f} sn")

    acik_adisyonlar = {
        a['adisyon__masa_id']: a['toplam']
        for a in (
            SiparisItem.objects
            .filter(
                adisyon__masa__sube=sube,
                adisyon__durum='Acik',
                iptal_edildi=False
            )
            .values('adisyon__masa_id')
            .annotate(toplam=Sum(F('adet') * F('urun__fiyat')))
        )
    }

    t4 = time.time()
    print(f"sube_detay -> acik_adisyonlar: {t4 - t3:.3f} sn")

    masa_listesi = []
    for masa in masalar:
        rezervasyonlar = list(masa.rezervasyon_set.all())
        rezervasyon = rezervasyonlar[0] if rezervasyonlar else None

        su_anki_tutar = acik_adisyonlar.get(masa.id, 0)

        masa_listesi.append({
            'id': masa.id,
            'masa_no': masa.masa_no,
            'dolu_mu': masa.dolu_mu,
            'su_anki_tutar': su_anki_tutar,
            'rezervasyon_var': bool(rezervasyon),
            'rezervasyon_saat': rezervasyon.saat if rezervasyon else None,
            'rezervasyon_musteri': rezervasyon.musteri_adi if rezervasyon else None,
            'pos_x': masa.pos_x,
            'pos_y': masa.pos_y,
            'genislik': masa.genislik,
            'yukseklik': masa.yukseklik,
        })

    t5 = time.time()
    print(f"sube_detay -> masa dongusu: {t5 - t4:.3f} sn")
    print(f"sube_detay -> toplam: {t5 - start_total:.3f} sn")

    return render(request, 'adisyon_modulu/sube_masalar.html', {
        'sube': sube,
        'masa_listesi': masa_listesi,
        'paketler': paketler,
        'kritik_stoklar': kritik_stoklar,
        'bekleyen_menu_talepleri': bekleyen_menu_talepleri[:6],
        'bekleyen_menu_talep_sayisi': bekleyen_menu_talepleri.count(),
        'bugun': bugun,
    })

@login_required
def masa_detay(request, masa_id):
    start_total = time.time()
    bugun = timezone.now().date()

    masa = get_object_or_404(
        Masa.objects.select_related('sube'),
        id=masa_id
    )

    t1 = time.time()
    print(f"masa_detay -> masa cekme: {t1 - start_total:.3f} sn")

    adisyon = (
        Adisyon.objects
        .filter(masa=masa, durum='Acik')
        .select_related('masa', 'sube', 'musteri', 'garson')
        .prefetch_related(
            Prefetch(
                'siparisler',
                queryset=SiparisItem.objects.select_related('urun', 'adisyon').order_by('id')
            )
        )
        .first()
    )

    # 🔥 BURASI DOĞRU YER
    if not adisyon:
        adisyon = Adisyon.objects.create(
            masa=masa,
            sube=masa.sube,
            siparis_turu='Masa',
            durum='Acik'
        )

    t2 = time.time()
    print(f"masa_detay -> adisyon: {t2 - t1:.3f} sn")

    urun_sorgu = (
        Urun.objects
        .filter(bolge__sube=masa.sube)
        .select_related('kategori', 'bolge')
        .order_by('sira', 'ad')
    )

    t3 = time.time()
    print(f"masa_detay -> urun_sorgu: {t3 - t2:.3f} sn")

    kategoriler = (
        Kategori.objects
        .prefetch_related(Prefetch('urunler', queryset=urun_sorgu))
        .order_by('sira', 'ad')
    )

    t4 = time.time()
    print(f"masa_detay -> kategoriler: {t4 - t3:.3f} sn")

    musteriler = Musteri.objects.all().order_by('ad_soyad')[:50]

    t5 = time.time()
    print(f"masa_detay -> musteriler: {t5 - t4:.3f} sn")

    rezervasyon = (
        masa.rezervasyon_set
        .filter(tarih=bugun, durum__in=['Onaylandı', 'Bekliyor'])
        .order_by('saat')
        .first()
    )

    t6 = time.time()
    print(f"masa_detay -> rezervasyon: {t6 - t5:.3f} sn")

    diger_masalar = (
        masa.sube.masalar
        .exclude(id=masa.id)
        .order_by('masa_no')
    )

    t7 = time.time()
    print(f"masa_detay -> diger_masalar: {t7 - t6:.3f} sn")
    print(f"masa_detay -> toplam: {t7 - start_total:.3f} sn")

    return render(request, 'adisyon_modulu/masa_detay.html', {
        'masa': masa,
        'sube': masa.sube,
        'adisyon': adisyon,
        'kategoriler': kategoriler,
        'musteriler': musteriler,
        'rezervasyon': rezervasyon,
        'diger_masalar': diger_masalar,
    })

@login_required
@user_passes_test(siparis_girebilir_mi)
def siparis_ekle(request, masa_id):
    if request.method != "POST":
        return JsonResponse({"status": "error"}, status=400)

    masa = Masa.objects.only('id', 'sube_id', 'dolu_mu').get(id=masa_id)

    urun_id = int(request.POST.get('urun_id'))
    adet = int(request.POST.get('adet', 1))

    adisyon = Adisyon.objects.filter(
        masa_id=masa_id,
        durum='Acik'
    ).first()

    if not adisyon:
        adisyon = Adisyon.objects.create(
            masa_id=masa_id,
            sube_id=masa.sube_id,
            siparis_turu='Masa',
            durum='Acik'
        )

    hareket_zamani = timezone.now()

    qs = SiparisItem.objects.filter(
        adisyon_id=adisyon.id,
        urun_id=urun_id,
        yazdirildi=False,
        iptal_edildi=False
    )

    if qs.exists():
        qs.update(adet=F('adet') + adet, siparisi_alan=request.user, son_siparis_hareketi=hareket_zamani)
        item = qs.select_related('urun').first()
    else:
        item = SiparisItem.objects.create(
            adisyon_id=adisyon.id,
            urun_id=urun_id,
            adet=adet,
            yazdirildi=False,
            siparisi_alan=request.user,
            son_siparis_hareketi=hareket_zamani,
        )
    receteden_stok_dus(item)

    if not masa.dolu_mu:
        Masa.objects.filter(id=masa_id, dolu_mu=False).update(dolu_mu=True)

    return JsonResponse({
        "status": "ok",
        "adisyon_id": adisyon.id,

        "item": {
            "id": item.id,
            "urun": item.urun.ad,
            "adet": item.adet,
            "fiyat": float(item.urun.fiyat),
            "toplam": float(item.toplam_fiyat()),
            "ikram_mi": item.ikram_mi,
            "hazir_mi": item.hazir_mi,
            "ozel_istek": item.ozel_istek or "",

            "url_sil": reverse('siparis_sil', args=[item.id]),
            "url_ikram": reverse('ikram_yap', args=[item.id]),
            "url_adet_azalt": reverse('siparis_adet_azalt', args=[item.id]),
            "url_adet_artir": reverse('siparis_adet_artir', args=[item.id]),
            "url_ozel_istek": reverse('siparis_ozel_istek', args=[item.id]),
        },

        "ara_toplam": float(adisyon.ara_toplam()),
        "toplam_tutar": float(adisyon.toplam_tutar()),
    })

@login_required
@user_passes_test(siparis_girebilir_mi)
def siparis_sil(request, item_id):
    item = get_object_or_404(
        SiparisItem.objects.select_related('adisyon', 'adisyon__masa', 'adisyon__sube', 'urun'),
        id=item_id
    )
    m_id = item.adisyon.masa.id if item.adisyon.masa else None
    a_id = item.adisyon.id

    if request.method == "POST":
        iptal_adet = int(request.POST.get('iptal_adet', item.adet))

        if iptal_adet >= item.adet:
            IptalKaydi.objects.create(
                sube=item.adisyon.sube,
                urun_adi=item.urun.ad,
                adet=item.adet,
                tutar=item.toplam_fiyat(),
                garson=request.user,
                sebep=request.POST.get('sebep')
            )
            item_adi = item.urun.ad
            item.delete()
            messages.success(request, f"{item_adi} tamamen iptal edildi.")

        elif iptal_adet > 0:
            IptalKaydi.objects.create(
                sube=item.adisyon.sube,
                urun_adi=item.urun.ad,
                adet=iptal_adet,
                tutar=item.urun.fiyat * iptal_adet,
                garson=request.user,
                sebep=request.POST.get('sebep')
            )
            item.adet -= iptal_adet
            item.save(update_fields=['adet'])
            messages.success(request, f"{item.urun.ad} - {iptal_adet} adet iptal edildi.")

        return redirect('masa_detay', masa_id=m_id) if m_id else redirect('paket_detay', adisyon_id=a_id)

    return render(request, 'adisyon_modulu/iptal_onay.html', {'item': item})


@login_required
@user_passes_test(siparis_girebilir_mi)
def ikram_yap(request, item_id):
    item = get_object_or_404(
        SiparisItem.objects.select_related('adisyon', 'adisyon__masa'),
        id=item_id
    )
    item.ikram_mi = not item.ikram_mi
    item.save(update_fields=['ikram_mi'])
    return redirect('masa_detay', masa_id=item.adisyon.masa.id) if item.adisyon.masa else redirect('paket_detay', adisyon_id=item.adisyon.id)


@login_required
@user_passes_test(siparis_girebilir_mi)
def indirim_yap(request, adisyon_id):
    adisyon = get_object_or_404(Adisyon.objects.select_related('masa'), id=adisyon_id)
    if request.method == "POST":
        try:
            adisyon.indirim_tutari = float(request.POST.get('indirim_tutari', 0))
            adisyon.save(update_fields=['indirim_tutari'])
        except ValueError:
            pass
    return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)


@login_required
@user_passes_test(siparis_girebilir_mi)
def masa_kapat(request, adisyon_id):
    a = get_object_or_404(
        Adisyon.objects.select_related('masa', 'sube').prefetch_related(
            Prefetch(
                'siparisler',
                queryset=SiparisItem.objects.select_related('urun').order_by('id')
            )
        ),
        id=adisyon_id
    )
    orijinal_masa = a.masa
    if a.masa is None:
        a.masa = SimpleNamespace(masa_no='Paket')

    if request.method == "POST":
        a.nakit_odenen = float(request.POST.get('nakit_tutar', 0) or 0)
        a.kart_odenen = float(request.POST.get('kart_tutar', 0) or 0)
    else:
        tur = request.GET.get('tur', 'Nakit')
        tutar = float(a.toplam_tutar())
        if tur == 'Nakit':
            a.nakit_odenen = tutar
            a.kart_odenen = 0
        else:
            a.kart_odenen = tutar
            a.nakit_odenen = 0

    a.durum = 'Kapali'
    a.garson = request.user
    a.save()

    try:
        yazici = Yazici.objects.filter(sube=a.sube).first()
        if yazici:
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
            komutlar.extend(ESC + b'\x40')
            komutlar.extend(ESC + b'\x61' + b'\x01')
            komutlar.extend(ESC + b'\x21' + b'\x30')
            komutlar.extend("LAR".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x00')
            komutlar.extend("MUSTERI FISI".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(turkce_duzelt(f"Sube: {a.sube.ad}").encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(f"MASA: {a.masa.masa_no if a.masa else 'Paket'}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(f"TARIH: {time.strftime('%d.%m.%Y %H:%M')}".encode('utf-8'))
            komutlar.extend(b'\x0a\x0a')

            komutlar.extend(ESC + b'\x61' + b'\x00')

            for item in a.siparisler.all():
                if not item.ikram_mi:
                    urun_adi = turkce_duzelt(item.urun.ad)
                    komutlar.extend(f"{urun_adi}".encode('utf-8'))
                    komutlar.extend(b'\x0a')
                    komutlar.extend(
                        f"  {item.adet} x {float(item.urun.fiyat):.2f}TL = {float(item.toplam_fiyat()):.2f}TL".encode('utf-8')
                    )
                    komutlar.extend(b'\x0a')
                    komutlar.extend(b'\x0a')

            komutlar.extend(("=" * 32).encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(f"ARA TOPLAM: {a.ara_toplam()}TL".encode('utf-8'))
            komutlar.extend(b'\x0a')
            if a.indirim_tutari > 0:
                komutlar.extend(f"INDIRIM: -{a.indirim_tutari}TL".encode('utf-8'))
                komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x11')
            komutlar.extend(f"TOPLAM: {a.toplam_tutar()}TL".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x00')

            komutlar.extend(b'\x0a')
            komutlar.extend(f"NAKIT: {a.nakit_odenen}TL".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(f"KART: {a.kart_odenen}TL".encode('utf-8'))
            komutlar.extend(b'\x0a')

            toplam_odeme = float(a.nakit_odenen) + float(a.kart_odenen)
            toplam_tutar = float(a.toplam_tutar())
            para_ustu = toplam_odeme - toplam_tutar

            if para_ustu > 0:
                komutlar.extend(f"PARA USTU: {para_ustu:.2f}TL".encode('utf-8'))
                komutlar.extend(b'\x0a')

            komutlar.extend(b'\x0a')
            komutlar.extend("TESEKKUR EDERIZ".encode('utf-8'))
            komutlar.extend(b'\x0a\x0a')
            komutlar.extend(GS + b'\x56' + b'\x41' + b'\x00')

            yaziciya_veri_gonder(yazici, komutlar)
            logger.info("Müşteri fişi yazdırıldı - Masa %s", a.masa.masa_no)

    except Exception as e:
        logger.warning("Fiş yazdırma hatası: %s", str(e))
        messages.warning(request, f"Fiş yazdırılamadı: {str(e)}")

    if orijinal_masa:
        orijinal_masa.dolu_mu = False
        orijinal_masa.save(update_fields=['dolu_mu'])

    return redirect('sube_detay', sube_id=a.sube.id if a.sube else 1)


@login_required
@user_passes_test(siparis_girebilir_mi)
def masa_tasi_birlestir(request, adisyon_id):
    if request.method == "POST":
        mevcut = get_object_or_404(
            Adisyon.objects.select_related('masa', 'sube'),
            id=adisyon_id
        )
        hedef_masa = get_object_or_404(
            Masa.objects.select_related('sube'),
            id=request.POST.get('hedef_masa_id')
        )

        eski_masa = mevcut.masa
        hedef_adisyon = Adisyon.objects.filter(masa=hedef_masa, durum='Acik').first()

        if hedef_adisyon:
            # Mevcut adisyondaki indirimleri hedef adisyona aktar (indirim kaybolmasın)
            if mevcut.indirim_tutari:
                hedef_adisyon.indirim_tutari = float(hedef_adisyon.indirim_tutari or 0) + float(mevcut.indirim_tutari)
                hedef_adisyon.save(update_fields=['indirim_tutari'])
            mevcut.siparisler.all().update(adisyon=hedef_adisyon)
            mevcut.delete()
        else:
            mevcut.masa = hedef_masa
            mevcut.save(update_fields=['masa'])
            if not hedef_masa.dolu_mu:
                hedef_masa.dolu_mu = True
                hedef_masa.save(update_fields=['dolu_mu'])

        if eski_masa:
            baska_adisyon_var = Adisyon.objects.filter(masa=eski_masa, durum='Acik').exists()
            if not baska_adisyon_var:
                eski_masa.dolu_mu = False
                eski_masa.save(update_fields=['dolu_mu'])

        return redirect('sube_detay', sube_id=hedef_masa.sube.id)

    return redirect('ana_sayfa')


@login_required
@user_passes_test(siparis_girebilir_mi)
def siparis_adet_artir(request, item_id):
    item = get_object_or_404(
        SiparisItem.objects.select_related('adisyon', 'adisyon__masa', 'urun'),
        id=item_id
    )
    item.adet += 1
    item.siparisi_alan = request.user
    item.son_siparis_hareketi = timezone.now()
    item.save(update_fields=['adet', 'siparisi_alan', 'son_siparis_hareketi'])
    messages.success(request, f"{item.urun.ad} adedi artırıldı.")

    return redirect('masa_detay', masa_id=item.adisyon.masa.id) if item.adisyon.masa else redirect('paket_detay', adisyon_id=item.adisyon.id)


@login_required
@user_passes_test(siparis_girebilir_mi)
def siparis_adet_azalt(request, item_id):
    item = get_object_or_404(
        SiparisItem.objects.select_related('adisyon', 'adisyon__masa', 'urun'),
        id=item_id
    )

    if item.adet > 1:
        item.adet -= 1
        item.siparisi_alan = request.user
        item.son_siparis_hareketi = timezone.now()
        item.save(update_fields=['adet', 'siparisi_alan', 'son_siparis_hareketi'])
        messages.success(request, f"{item.urun.ad} adedi azaltıldı.")
    else:
        return redirect('siparis_sil', item_id=item.id)

    return redirect('masa_detay', masa_id=item.adisyon.masa.id) if item.adisyon.masa else redirect('paket_detay', adisyon_id=item.adisyon.id)


@login_required
@user_passes_test(siparis_girebilir_mi)
def siparis_ozel_istek(request, item_id):
    item = get_object_or_404(
        SiparisItem.objects.select_related('adisyon', 'adisyon__masa', 'urun'),
        id=item_id
    )

    if request.method == "POST":
        item.ozel_istek = request.POST.get('ozel_istek', '')
        item.siparisi_alan = request.user
        item.son_siparis_hareketi = timezone.now()
        item.save(update_fields=['ozel_istek', 'siparisi_alan', 'son_siparis_hareketi'])
        messages.success(request, f"{item.urun.ad} için özel istek kaydedildi.")

    return redirect('masa_detay', masa_id=item.adisyon.masa.id) if item.adisyon.masa else redirect('paket_detay', adisyon_id=item.adisyon.id)


@login_required
@user_passes_test(siparis_girebilir_mi)
def adisyon_musteri_ekle(request, adisyon_id):
    adisyon = get_object_or_404(
        Adisyon.objects.select_related('masa'),
        id=adisyon_id
    )

    if request.method == 'POST':
        musteri_id = request.POST.get('musteri_id')
        musteri = get_object_or_404(Musteri, id=musteri_id)

        adisyon.musteri = musteri
        adisyon.save(update_fields=['musteri'])

        messages.success(request, f'{musteri.ad_soyad} adisyona eklendi.')

    return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)


@login_required
@user_passes_test(siparis_girebilir_mi)
def kisisel_indirim_uygula(request, indirim_id, adisyon_id):
    """
    Kişisel indirimi adisyona uygula.
    Modeldeki metod (indirim_uygula) çağrılarak kod tekrarı (DRY) engellenmiştir.
    """
    indirim = get_object_or_404(KisiselIndirim, id=indirim_id, aktif=True)
    adisyon = get_object_or_404(Adisyon, id=adisyon_id, durum='Acik')
    
    if not adisyon.musteri or indirim.musteri.id != adisyon.musteri.id:
        messages.error(request, "Bu indirim bu müşteriye ait değil veya müşteri seçili değil!")
        return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)
        
    basarili, mesaj = indirim.indirim_uygula(adisyon)
    
    if basarili:
        messages.success(request, f"✅ {mesaj}")
    else:
        messages.error(request, f"❌ {mesaj}")
        
    return redirect('masa_detay', masa_id=adisyon.masa.id) if adisyon.masa else redirect('paket_detay', adisyon_id=adisyon.id)


@login_required
def garson_paneli(request):
    bekleyen_cagrilar = (
        GarsonCagri.objects
        .filter(tamamlandi_mi=False)
        .select_related('sube')
        .order_by('-zaman')
    )

    return render(request, 'adisyon_modulu/garson/garson_paneli.html', {
        'bekleyen_cagrilar': bekleyen_cagrilar,
        'back_url': _safe_next_url(request, 'ana_sayfa'),
    })


@login_required
def garson_cagri_tamamla(request, cagri_id):
    cagri = get_object_or_404(GarsonCagri, id=cagri_id)
    redirect_url = _safe_next_url(request, 'garson_paneli')

    if request.method == 'POST':
        cagri.tamamlandi_mi = True
        cagri.save(update_fields=['tamamlandi_mi'])

    return redirect(redirect_url)


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
@require_http_methods(["GET", "POST"])
def api_garson_cagir(request, sube_id):
    masa_no = request.POST.get("masa") or request.GET.get("masa")

    if not masa_no and request.body:
        try:
            data = json.loads(request.body.decode("utf-8"))
            masa_no = data.get("masa")
        except Exception:
            pass

    if not masa_no:
        return JsonResponse({"success": False, "message": "Masa bilgisi yok"}, status=400)

    masa_no = str(masa_no).strip()

    masa = Masa.objects.filter(sube_id=sube_id, masa_no=masa_no).first()
    if not masa:
        return JsonResponse({"success": False, "message": f"Masa bulunamadı: {masa_no}"}, status=404)

    mevcut_cagri = GarsonCagri.objects.filter(
        sube_id=sube_id,
        masa_no=masa_no,
        goruldu_mu=False
    ).order_by('-zaman').first()

    if mevcut_cagri:
        return JsonResponse({
            "success": True,
            "id": mevcut_cagri.id,
            "message": f"Masa {masa_no} için zaten bekleyen çağrı var."
        })

    cagri = GarsonCagri.objects.create(
        sube_id=sube_id,
        masa_no=masa_no,
        goruldu_mu=False
    )

    return JsonResponse({
        "success": True,
        "id": cagri.id,
        "message": "Garson çağrısı oluşturuldu."
    })

@login_required
def garson_tamamlananlari_temizle(request):
    redirect_url = _safe_next_url(request, 'garson_paneli')
    if request.method == 'POST':
        silinen, _ = GarsonCagri.objects.filter(tamamlandi_mi=True).delete()
        messages.success(request, f'{silinen} adet tamamlanmış garson çağrısı silindi.')

    return redirect(redirect_url)

@csrf_exempt
@require_http_methods(["POST"])
def api_masa_plani_kaydet(request):
    try:
        if request.content_type and 'application/json' in request.content_type:
            data = json.loads(request.body)
        else:
            data = request.POST.dict()
            if 'masalar' in data and isinstance(data['masalar'], str):
                data['masalar'] = json.loads(data['masalar'])

        sube_id = data.get('sube_id')
        if sube_id:
            sube = Sube.objects.filter(id=sube_id).first()
            if sube:
                if 'kroki_w' in data:
                    sube.masa_plani_genislik = int(float(data['kroki_w']))
                if 'kroki_h' in data:
                    sube.masa_plani_yukseklik = int(float(data['kroki_h']))
                
                if 'kroki_arkaplan' in request.FILES:
                    sube.kroki_arkaplan = request.FILES['kroki_arkaplan']
                sube.save()

        masalar = data.get('masalar', [])
        for item in masalar:
            masa_id = item.get('id')
            if isinstance(masa_id, str):
                import re
                match = re.search(r'\d+', masa_id)
                if match:
                    masa_id = int(match.group())
            if masa_id:
                Masa.objects.filter(id=masa_id).update(
                    pos_x=float(item.get('x', 0)),
                    pos_y=float(item.get('y', 0)),
                    genislik=float(item.get('w', 120)),
                    yukseklik=float(item.get('h', 120))
                )
        return JsonResponse({'success': True})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


# ===== MASA YÖNETİMİ VIEW'LARI =====

@login_required
@user_passes_test(lambda u: u.is_superuser)
def masa_yonetim_listesi(request):
    """Şubenin masalarını yönet (ekle/sil)"""
    subeler = Sube.objects.all().order_by('ad')
    
    # Eğer bir sube seçilmişse o şubenin masalarını göster
    sube_id = request.GET.get('sube_id') or request.POST.get('sube_id')
    secili_sube = None
    masalar = []
    
    if sube_id:
        try:
            secili_sube = Sube.objects.get(id=sube_id)
            masalar = secili_sube.masalar.all().order_by('masa_no')
        except Sube.DoesNotExist:
            messages.error(request, 'Şube bulunamadı.')
    elif subeler.exists():
        secili_sube = subeler.first()
        masalar = secili_sube.masalar.all().order_by('masa_no')
    
    # Masa ekleme formu
    if request.method == 'POST' and 'ekle' in request.POST:
        from ..forms import MasaEkleForm
        form = MasaEkleForm(request.POST)
        if form.is_valid() and secili_sube:
            masa = form.save(commit=False)
            masa.sube = secili_sube
            
            # Masa numarası aynı şubede benzersiz olmalı
            if Masa.objects.filter(sube=secili_sube, masa_no=masa.masa_no).exists():
                messages.error(request, f'Bu şubede "{masa.masa_no}" masa numarası zaten mevcut.')
            else:
                masa.save()
                messages.success(request, f'"{masa.masa_no}" numarası masa başarıyla eklendi.')
                masalar = secili_sube.masalar.all().order_by('masa_no')
        else:
            messages.error(request, 'Form hatalı. Lütfen kontrol edin.')
    
    from ..forms import MasaEkleForm
    form = MasaEkleForm()
    
    return render(request, 'adisyon_modulu/masa_yonetim.html', {
        'subeler': subeler,
        'secili_sube': secili_sube,
        'masalar': masalar,
        'form': form,
    })


@login_required
@user_passes_test(lambda u: u.is_superuser)
def masa_sil(request, masa_id):
    """Masa sil"""
    masa = get_object_or_404(Masa, id=masa_id)
    sube_id = masa.sube.id
    
    # Masa üzerinde açık adisyon var mı kontrol et
    acik_adisyon = Adisyon.objects.filter(masa=masa, durum='Acik').exists()
    
    if acik_adisyon:
        messages.error(request, f'"{masa.masa_no}" masasında açık adisyon var. Lütfen önce adisyonu kapatın.')
        return redirect('masa_yonetim_listesi', sube_id=sube_id)
    
    masa_no = masa.masa_no
    masa.delete()
    messages.success(request, f'"{masa_no}" numarası masa silindi.')
    
    return redirect('masa_yonetim_listesi', sube_id=sube_id)
