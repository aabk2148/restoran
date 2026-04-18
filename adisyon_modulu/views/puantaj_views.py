from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone

from ..models import PersonelPuantaj


YONETIM_ROLLERI = {'Yonetici', 'Kasa', 'Muhasebe'}


@login_required
def puantaj_paneli(request):
    profil = getattr(request.user, 'profil', None)
    rol = getattr(profil, 'rol', None)
    sube = getattr(profil, 'sube', None)

    bugun = timezone.localdate()
    aktif_kayit = (
        PersonelPuantaj.objects
        .filter(user=request.user, cikis_saati__isnull=True)
        .order_by('-giris_saati')
        .first()
    )

    kayitlar = PersonelPuantaj.objects.select_related('user', 'sube')
    if rol not in YONETIM_ROLLERI and not request.user.is_superuser:
        kayitlar = kayitlar.filter(user=request.user)
    elif sube:
        kayitlar = kayitlar.filter(sube=sube)

    bugun_kayitlari = kayitlar.filter(tarih=bugun)
    son_kayitlar = kayitlar[:40]

    return render(request, 'adisyon_modulu/puantaj_paneli.html', {
        'aktif_kayit': aktif_kayit,
        'bugun_kayitlari': bugun_kayitlari,
        'son_kayitlar': son_kayitlar,
        'bugun': bugun,
        'yonetim_gorunumu': rol in YONETIM_ROLLERI or request.user.is_superuser,
    })


@login_required
def puantaj_hareketi(request):
    if request.method != 'POST':
        return redirect('puantaj_paneli')

    aktif_kayit = (
        PersonelPuantaj.objects
        .filter(user=request.user, cikis_saati__isnull=True)
        .order_by('-giris_saati')
        .first()
    )
    notu = (request.POST.get('notu') or '').strip()

    if aktif_kayit:
        aktif_kayit.cikis_saati = timezone.now()
        if notu:
            aktif_kayit.notu = notu
        aktif_kayit.save(update_fields=['cikis_saati', 'notu'])
        messages.success(request, "Cikis saati kaydedildi.")
    else:
        profil = getattr(request.user, 'profil', None)
        PersonelPuantaj.objects.create(
            user=request.user,
            sube=getattr(profil, 'sube', None),
            tarih=timezone.localdate(),
            giris_saati=timezone.now(),
            notu=notu or None,
        )
        messages.success(request, "Giris saati kaydedildi.")

    return redirect('puantaj_paneli')
