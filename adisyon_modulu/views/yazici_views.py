from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import get_object_or_404, redirect, render

from ..forms import YaziciAdminForm
from ..models import Yazici
from .auth_views import yonetici_mi


@login_required
@user_passes_test(yonetici_mi)
def yazici_yonetimi(request):
    duzenlenen = None
    yazici_id = request.GET.get("duzenle")
    if yazici_id:
        duzenlenen = get_object_or_404(Yazici, pk=yazici_id)

    if request.method == "POST":
        islem = request.POST.get("islem", "kaydet")

        if islem == "sil":
            silinecek = get_object_or_404(Yazici, pk=request.POST.get("yazici_id"))
            yazici_adi = silinecek.ad
            silinecek.delete()
            messages.success(request, f"{yazici_adi} yazicisi silindi.")
            return redirect("yazici_yonetimi")

        form = YaziciAdminForm(request.POST, instance=duzenlenen)
        if form.is_valid():
            kayit = form.save()
            mesaj = "Yazici guncellendi." if duzenlenen else "Yeni yazici eklendi."
            messages.success(request, mesaj)
            return redirect("yazici_yonetimi")
    else:
        form = YaziciAdminForm(instance=duzenlenen)

    context = {
        "form": form,
        "duzenlenen": duzenlenen,
        "yazicilar": Yazici.objects.select_related("sube").order_by("sube__ad", "ad"),
    }
    return render(request, "adisyon_modulu/yazici_yonetimi.html", context)
