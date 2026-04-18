import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.http import JsonResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from ..models import Adisyon, Masa, MenuSiparisTalebi, MenuSiparisTalepKalemi, Sube, SiparisItem, Urun
from .auth_views import menu_siparis_onaylayabilir_mi


def _safe_next_url(request, fallback_name):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return next_url
    return reverse(fallback_name)


def _istemci_ip_al(request):
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@csrf_exempt
@require_POST
def menu_siparis_talebi_olustur(request, sube_id):
    sube = get_object_or_404(Sube, id=sube_id)

    try:
        data = json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'success': False, 'message': 'Gecersiz siparis verisi.'}, status=400)

    masa_no = str(data.get('masa') or '').strip()
    kalemler = data.get('items') or []
    musteri_notu = (data.get('musteri_notu') or '').strip()

    if not masa_no:
        return JsonResponse({'success': False, 'message': 'Masa bilgisi gerekli.'}, status=400)
    if not kalemler:
        return JsonResponse({'success': False, 'message': 'Sepet bos olamaz.'}, status=400)

    urun_idler = []
    for item in kalemler:
        try:
            urun_idler.append(int(item.get('urun_id')))
        except (TypeError, ValueError):
            return JsonResponse({'success': False, 'message': 'Gecersiz urun secimi.'}, status=400)

    masa = Masa.objects.filter(sube=sube, masa_no=masa_no).first()
    if not masa:
        return JsonResponse({'success': False, 'message': f'Masa bulunamadi: {masa_no}'}, status=404)

    urunler = {urun.id: urun for urun in Urun.objects.filter(id__in=urun_idler, bolge__sube=sube)}
    if len(urunler) != len(set(urun_idler)):
        return JsonResponse({'success': False, 'message': 'Sepette gecersiz urun var.'}, status=400)

    with transaction.atomic():
        talep = MenuSiparisTalebi.objects.create(
            sube=sube,
            masa=masa,
            masa_no=masa_no,
            musteri_notu=musteri_notu or None,
            olusturan_ip=_istemci_ip_al(request),
        )

        for item in kalemler:
            urun_id = int(item.get('urun_id'))
            adet = max(int(item.get('adet', 1)), 1)
            ozel_istek = (item.get('ozel_istek') or '').strip()
            MenuSiparisTalepKalemi.objects.create(
                talep=talep,
                urun=urunler[urun_id],
                adet=adet,
                ozel_istek=ozel_istek or None,
            )

    return JsonResponse({
        'success': True,
        'message': 'Siparis talebiniz alindi. Kasa veya yonetici onayindan sonra mutfaga iletilecek.',
        'talep_id': talep.id,
    })


@login_required
@user_passes_test(menu_siparis_onaylayabilir_mi)
def menu_siparis_onay_listesi(request):
    profil = getattr(request.user, 'profil', None)
    sube = getattr(profil, 'sube', None)

    talepler = (
        MenuSiparisTalebi.objects
        .select_related('sube', 'masa', 'onaylayan', 'adisyon')
        .prefetch_related('kalemler__urun')
        .order_by('-olusturma_zamani')
    )
    if sube and not request.user.is_superuser:
        talepler = talepler.filter(sube=sube)

    back_url = _safe_next_url(request, 'ana_sayfa')
    return render(request, 'adisyon_modulu/menu_siparis_onay_listesi.html', {
        'bekleyen_talepler': talepler.filter(durum='Beklemede'),
        'sonuclanan_talepler': talepler.exclude(durum='Beklemede')[:20],
        'back_url': back_url,
    })


@login_required
@user_passes_test(menu_siparis_onaylayabilir_mi)
@require_POST
def menu_siparis_onayla(request, talep_id):
    talep = get_object_or_404(
        MenuSiparisTalebi.objects.select_related('sube', 'masa').prefetch_related('kalemler__urun'),
        id=talep_id
    )
    redirect_url = _safe_next_url(request, 'menu_siparis_onay_listesi')
    if talep.durum != 'Beklemede':
        messages.warning(request, 'Bu siparis talebi zaten islenmis.')
        return redirect(redirect_url)

    hareket_zamani = timezone.now()

    with transaction.atomic():
        adisyon = (
            Adisyon.objects
            .filter(masa=talep.masa, durum='Acik')
            .select_for_update()
            .first()
        )
        if not adisyon:
            adisyon = Adisyon.objects.create(
                masa=talep.masa,
                sube=talep.sube,
                siparis_turu='Masa',
                durum='Acik',
            )

        for kalem in talep.kalemler.all():
            SiparisItem.objects.create(
                adisyon=adisyon,
                urun=kalem.urun,
                adet=kalem.adet,
                ozel_istek=kalem.ozel_istek,
                yazdirildi=False,
                siparisi_alan=request.user,
                son_siparis_hareketi=hareket_zamani,
            )

        if talep.masa and not talep.masa.dolu_mu:
            talep.masa.dolu_mu = True
            talep.masa.save(update_fields=['dolu_mu'])

        talep.durum = 'Onaylandi'
        talep.onaylayan = request.user
        talep.onay_zamani = timezone.now()
        talep.adisyon = adisyon
        talep.save(update_fields=['durum', 'onaylayan', 'onay_zamani', 'adisyon'])

    messages.success(request, f"Masa {talep.masa_no} icin menu siparisi onaylandi.")
    return redirect(redirect_url)


@login_required
@user_passes_test(menu_siparis_onaylayabilir_mi)
@require_POST
def menu_siparis_reddet(request, talep_id):
    talep = get_object_or_404(MenuSiparisTalebi, id=talep_id)
    redirect_url = _safe_next_url(request, 'menu_siparis_onay_listesi')
    if talep.durum != 'Beklemede':
        messages.warning(request, 'Bu siparis talebi zaten islenmis.')
        return redirect(redirect_url)

    red_sebebi = (request.POST.get('red_sebebi') or '').strip()
    talep.durum = 'Reddedildi'
    talep.red_sebebi = red_sebebi or None
    talep.onaylayan = request.user
    talep.onay_zamani = timezone.now()
    talep.save(update_fields=['durum', 'red_sebebi', 'onaylayan', 'onay_zamani'])

    messages.success(request, f"Masa {talep.masa_no} icin menu siparisi reddedildi.")
    return redirect(redirect_url)
