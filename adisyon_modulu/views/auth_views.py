# views/auth_views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils import timezone
from ..models import Sube, KullaniciProfili
from ..dashboard import build_dashboard_context
from ..lisans import lisans
from ..module_control import is_module_enabled

# --- YETKİ KONTROL FONKSİYONLARI ---

def yonetici_mi(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profil') and user.profil.rol == 'Yonetici'))

def asci_mi(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profil') and user.profil.rol == 'Asci'))

def garson_mi(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profil') and user.profil.rol == 'Garson'))

def kasa_mi(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profil') and user.profil.rol == 'Kasa'))

def muhasebe_mi(user):
    return user.is_authenticated and (user.is_superuser or (hasattr(user, 'profil') and user.profil.rol == 'Muhasebe'))

def rapor_gorebilir_mi(user):
    """Raporları kimler görebilir? (Superuser, Yönetici, Muhasebe, Kasa)"""
    if not is_module_enabled('reports-panel'):
        return False
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'profil'):
        return user.profil.rol in ['Yonetici', 'Muhasebe', 'Kasa']
    return False

def mutfak_gorebilir_mi(user):
    """Mutfak ekranını kimler görebilir? (Superuser, Yönetici, Aşçı)"""
    if not is_module_enabled('kitchen-panel'):
        return False
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'profil'):
        return user.profil.rol in ['Yonetici', 'Asci']
    return False

def siparis_girebilir_mi(user):
    """Sipariş kimler girebilir? (Yönetici, Garson, Kasa)"""
    if not is_module_enabled('waiter-panel'):
        return False
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'profil'):
        return user.profil.rol in ['Yonetici', 'Garson', 'Kasa']
    return False


def menu_siparis_onaylayabilir_mi(user):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if hasattr(user, 'profil'):
        return user.profil.rol in ['Yonetici', 'Kasa']
    return False


def format_tl(tutar):
    if tutar is None: tutar = 0
    return "{:,.2f}".format(float(tutar)).replace(",", "X").replace(".", ",").replace("X", ".")


class ElakiLoginView(LoginView):
    template_name = 'registration/login.html'

    @staticmethod
    def _kvkk_onay_gerekli(username):
        username = (username or "").strip()
        if not username:
            return True

        user = User.objects.filter(username=username).select_related("profil").first()
        if not user:
            return True

        profil = getattr(user, "profil", None)
        return not getattr(profil, "kvkk_onaylandi", False)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["kvkk_link"] = "docs/KVK ve Lisans.pdf"

        form = context.get("form")
        user = form.get_user() if form and hasattr(form, "get_user") else None
        profil = getattr(user, "profil", None) if user else None
        username = ""
        if hasattr(self.request, "POST"):
            username = self.request.POST.get("username", "")

        context["kvkk_onay_gerekli"] = (
            not getattr(profil, "kvkk_onaylandi", False)
            if user else self._kvkk_onay_gerekli(username)
        )
        return context

    def form_valid(self, form):
        user = form.get_user()
        profil, _ = KullaniciProfili.objects.get_or_create(user=user)

        kvkk_onay_gerekli = not profil.kvkk_onaylandi
        kvkk_onay_verildi = self.request.POST.get("kvkk_onay") == "1"

        if kvkk_onay_gerekli and not kvkk_onay_verildi:
            form.add_error(None, "Devam etmeden once KVKK ve lisans metnini kabul etmelisiniz.")
            return self.form_invalid(form)

        if kvkk_onay_gerekli and kvkk_onay_verildi:
            profil.kvkk_onaylandi = True
            profil.kvkk_onay_tarihi = timezone.now()
            profil.save(update_fields=["kvkk_onaylandi", "kvkk_onay_tarihi"])

        return super().form_valid(form)


def kvkk_durum_kontrol(request):
    username = (request.GET.get("username") or "").strip()
    return JsonResponse({
        "kvkk_onay_gerekli": ElakiLoginView._kvkk_onay_gerekli(username)
    })


@login_required
def giris_sonrasi_yonlendir(request):
    if not hasattr(request.user, 'profil'): 
        return redirect('ana_sayfa')
    rol = request.user.profil.rol
    if rol == 'Asci': 
        return redirect('mutfak_ana_sayfa')
    return redirect('ana_sayfa')


@login_required
def ana_sayfa(request):
    if hasattr(request.user, 'profil') and request.user.profil.sube:
        return redirect('sube_detay', sube_id=request.user.profil.sube.id)
    context = {'subeler': Sube.objects.all()}
    context.update(build_dashboard_context(request.user))
    return render(request, 'adisyon_modulu/index.html', context)

def lisans_aktivasyon_view(request):
    """Lisans aktivasyon sayfası"""
    
    # Eğer zaten aktif lisans varsa ana sayfaya yönlendir
    gecerli, mesaj, sonuc = lisans.lisans_kontrol()
    if gecerli:
        messages.success(request, 'Lisansınız zaten aktif!')
        return redirect('ana_sayfa')
    
    if request.method == 'POST':
        lisans_kodu = request.POST.get('lisans_kodu', '').strip().upper()
        
        if not lisans_kodu:
            messages.error(request, 'Lütfen lisans kodunu girin.')
            return render(request, 'registration/lisans_aktivasyon.html')
        
        # Aktivasyon dene
        basarili, sonuc = lisans.aktivasyon_yap(lisans_kodu)
        
        if basarili:
            messages.success(request, 'Lisans başarıyla aktif edildi! Yönlendiriliyorsunuz...')
            return redirect('ana_sayfa')
        else:
            messages.error(request, f'Aktivasyon başarısız: {sonuc}')
    
    return render(request, 'registration/lisans_aktivasyon.html')

def index(request):
    if request.user.is_authenticated:
        if hasattr(request.user, "is_garson") and request.user.is_garson:
            return redirect("garson_paneli")
        elif request.user.is_superuser:
            return redirect("/admin/")
    return redirect("login")
