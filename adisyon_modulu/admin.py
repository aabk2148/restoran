from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.urls import reverse
from django.db import models
from django.utils import timezone
from .forms import HizliSatisCihazAdminForm, KullaniciProfiliAdminForm, ModulAyariAdminForm, YaziciAdminForm
from .models import *
from django.contrib import admin
from .models import StokKalemi
from .models import UretimFis

# ==================== KULLANICI PROFİLİ ====================
class KullaniciProfiliInline(admin.StackedInline):
    model = KullaniciProfili
    form = KullaniciProfiliAdminForm
    can_delete = False
    verbose_name_plural = 'Rol ve Şube Bilgileri'

class UserAdmin(BaseUserAdmin):
    inlines = (KullaniciProfiliInline,)
    list_display = ('username', 'get_rol', 'get_sube', 'email', 'is_staff', 'is_superuser')
    list_filter = ('is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'email')
    
    def get_rol(self, obj):
        return obj.profil.rol if hasattr(obj, 'profil') else "-"
    get_rol.short_description = 'Rol'
    
    def get_sube(self, obj):
        return obj.profil.sube.ad if hasattr(obj, 'profil') and obj.profil.sube else "-"
    get_sube.short_description = 'Şube'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# Admin panel başlığını özelleştirme
admin.site.site_header = "Restoran Otomasyon Sistemi"
admin.site.site_title = "Restoran Yönetim Paneli"
admin.site.index_title = "Modüller"

def user_is_role_admin(user):
    return user.is_authenticated and user.is_active and user.is_superuser

def admin_has_permission(self, request):
    return user_is_role_admin(request.user)

admin.site.has_permission = admin_has_permission.__get__(admin.site, admin.site.__class__)

_original_has_module_permission = admin.ModelAdmin.has_module_permission
_original_has_view_permission = admin.ModelAdmin.has_view_permission
_original_has_add_permission = admin.ModelAdmin.has_add_permission
_original_has_change_permission = admin.ModelAdmin.has_change_permission
_original_has_delete_permission = admin.ModelAdmin.has_delete_permission

def role_admin_has_module_permission(self, request):
    if user_is_role_admin(request.user):
        return True
    return _original_has_module_permission(self, request)

def role_admin_has_view_permission(self, request, obj=None):
    if user_is_role_admin(request.user):
        return True
    return _original_has_view_permission(self, request, obj=obj)

def role_admin_has_add_permission(self, request):
    if user_is_role_admin(request.user):
        return True
    return _original_has_add_permission(self, request)

def role_admin_has_change_permission(self, request, obj=None):
    if user_is_role_admin(request.user):
        return True
    return _original_has_change_permission(self, request, obj=obj)

def role_admin_has_delete_permission(self, request, obj=None):
    if user_is_role_admin(request.user):
        return True
    return _original_has_delete_permission(self, request, obj=obj)

admin.ModelAdmin.has_module_permission = role_admin_has_module_permission
admin.ModelAdmin.has_view_permission = role_admin_has_view_permission
admin.ModelAdmin.has_add_permission = role_admin_has_add_permission
admin.ModelAdmin.has_change_permission = role_admin_has_change_permission
admin.ModelAdmin.has_delete_permission = role_admin_has_delete_permission

# ==================== SOL MENÜ TÜRKÇE ALFABETİK SIRALAMA ====================
def tr_sort_key(item_name):
    char_map = {
        'c': 'c0', 'ç': 'c1', 'Ç': 'c1', 'C': 'c0',
        'g': 'g0', 'ğ': 'g1', 'Ğ': 'g1', 'G': 'g0',
        'ı': 'h1', 'I': 'h1', 'i': 'h2', 'İ': 'h2',
        'o': 'o0', 'ö': 'o1', 'Ö': 'o1', 'O': 'o0',
        's': 's0', 'ş': 's1', 'Ş': 's1', 'S': 's0',
        'u': 'u0', 'ü': 'u1', 'Ü': 'u1', 'U': 'u0',
    }
    return ''.join(char_map.get(c, c.lower()) for c in item_name)

def get_app_list(self, request, app_label=None):
    app_dict = self._build_app_dict(request, app_label)
    app_list = sorted(app_dict.values(), key=lambda x: tr_sort_key(x['name']))
    for app in app_list:
        app['models'].sort(key=lambda x: tr_sort_key(x['name']))
    return app_list

admin.site.get_app_list = get_app_list.__get__(admin.site, admin.site.__class__)


@admin.register(ModulAyari)
class ModulAyariAdmin(admin.ModelAdmin):
    form = ModulAyariAdminForm
    list_display = ('__str__', 'guncellenme_zamani')
    readonly_fields = ('guncellenme_zamani',)

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        if not request.user.is_superuser:
            return False
        if ModulAyari.objects.exists():
            return False
        return super().has_add_permission(request)

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.pk = 1
        super().save_model(request, obj, form, change)

# ==================== TEMEL MODELLER ====================
@admin.register(Sube)
class SubeAdmin(admin.ModelAdmin):
    list_display = ['ad', 'adres', 'masa_sayisi', 'yazici_sayisi']
    search_fields = ['ad']
    list_per_page = 25
    
    def masa_sayisi(self, obj):
        return obj.masalar.count()
    masa_sayisi.short_description = 'Masa Sayısı'
    
    def yazici_sayisi(self, obj):
        return obj.yazicilar.count()
    yazici_sayisi.short_description = 'Yazıcı Sayısı'

@admin.register(Yazici)
class YaziciAdmin(admin.ModelAdmin):
    form = YaziciAdminForm
    list_display = ['ad', 'sube', 'baglanti_tipi', 'baglanti_hedefi_goster', 'port', 'yazici_tipi', 'baglanti_durumu']
    list_filter = ['sube', 'yazici_tipi', 'baglanti_tipi']
    search_fields = ['ad', 'ip_adresi', 'windows_yazici_adi']
    list_editable = ['port']
    list_per_page = 25

    def baglanti_hedefi_goster(self, obj):
        return obj.baglanti_hedefi()
    baglanti_hedefi_goster.short_description = 'Baglanti'
    
    def baglanti_durumu(self, obj):
        # DÜZELTİLDİ: Parametre eklendi
        return format_html('<span style="color: green;">{} Aktif</span>', '✓')
    baglanti_durumu.short_description = 'Durum'

@admin.register(Bolge)
class BolgeAdmin(admin.ModelAdmin):
    list_display = ['ad', 'sube', 'yazici']
    list_filter = ['sube']
    list_per_page = 25

@admin.register(Kategori)
class KategoriAdmin(admin.ModelAdmin):
    list_display = ['ad', 'sira', 'urun_sayisi']
    list_editable = ['sira']
    search_fields = ['ad']
    list_per_page = 25
    
    def urun_sayisi(self, obj):
        return obj.urunler.count()
    urun_sayisi.short_description = 'Ürün Sayısı'

# ==================== ÜRÜN VE STOK ====================
class ReceteInline(admin.TabularInline):
    model = Recete
    extra = 1
    classes = ['collapse']

@admin.register(Urun)
class UrunAdmin(admin.ModelAdmin):
    list_display = ['ad', 'kategori', 'sira', 'fiyat', 'kdv_orani', 'receteli_mi', 'bolge', 'urun_gorseli']
    list_filter = ['kategori', 'bolge', 'kdv_orani', 'receteli_mi']
    search_fields = ['ad', 'aciklama']
    list_editable = ['sira', 'fiyat', 'kdv_orani']
    readonly_fields = ['urun_gorseli_preview']
    inlines = [ReceteInline]
    list_per_page = 25
    ordering = ('kategori', 'sira', 'ad')

    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('kategori', 'sira', 'ad', 'fiyat', 'kdv_orani', 'receteli_mi')
        }),
        ('Bölge ve Görsel', {
            'fields': ('bolge', 'gorsel', 'urun_gorseli_preview', 'aciklama')
        }),
        ('Alerjen Bilgileri', {
            'fields': ('alerjen_bilgisi',),
            'classes': ('collapse',)
        }),
    )

    def urun_gorseli(self, obj):
        if obj.gorsel:
            return format_html(
                '<img src="{}" width="50" height="50" style="object-fit: cover; border-radius: 5px;" />',
                obj.gorsel.url
            )
        return format_html('<span style="color: #999;">{}</span>', 'Görsel yok')
    urun_gorseli.short_description = 'Görsel'

    def urun_gorseli_preview(self, obj):
        if obj.gorsel:
            return format_html(
                '<img src="{}" width="200" style="border-radius: 5px; border: 1px solid #ddd;" />',
                obj.gorsel.url
            )
        return "Henüz görsel yüklenmemiş"
    urun_gorseli_preview.short_description = 'Görsel Önizleme'

@admin.register(StokKalemi)
class StokKalemiAdmin(admin.ModelAdmin):
    list_display = [
    'ad',
    'sube',
    'miktar',
    'birim',
    'kritik_seviye',
    'tedarikci',
    'stok_durumu',
    'son_kullanim_tarihi',
    'satilabilir_mi',
    'uretimde_kullanilir_mi',
    'otomatik_urun_olustur',
]
    list_filter = [
    'sube',
    'birim',
    'tedarikci',
    'satilabilir_mi',
    'uretimde_kullanilir_mi',
    'otomatik_urun_olustur',
]
    list_editable = ['miktar', 'kritik_seviye']
    search_fields = ['ad', 'barkod']
    list_per_page = 25
    actions = ['kritik_stok_uyarisi']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('sube', 'ad', 'birim', 'barkod')
        }),
        ('Stok Bilgileri', {
    'fields': (
        'miktar',
        'kritik_seviye',
        'fiyat',
        'satilabilir_mi',
        'uretimde_kullanilir_mi',
        'otomatik_urun_olustur',
        )
        }),
        ('Tedarikçi', {
            'fields': ('tedarikci',)
        }),
        ('Son Kullanma Tarihi', {
            'fields': ('son_kullanim_tarihi',)
        }),
            )
    
    def stok_durumu(self, obj):
        if obj.miktar <= 0:
            # DÜZELTİLDİ: Parametre eklendi
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', '🔴 Tükendi')
        elif obj.miktar <= obj.kritik_seviye:
            # DÜZELTİLDİ: Parametre eklendi
            return format_html('<span style="color: orange; font-weight: bold;">{}</span>', '🟡 Kritik')
        else:
            # DÜZELTİLDİ: Parametre eklendi
            return format_html('<span style="color: green; font-weight: bold;">{}</span>', '🟢 İyi')
    stok_durumu.short_description = 'Stok Durumu'
    
    def kritik_stok_uyarisi(self, request, queryset):
        kritikler = queryset.filter(miktar__lte=models.F('kritik_seviye'))
        self.message_user(request, f"{kritikler.count()} kritik stok kalemi var.")
    kritik_stok_uyarisi.short_description = "Kritik stokları kontrol et"

class StokHareketInline(admin.TabularInline):
    model = StokHareket
    extra = 0
    fields = ['tip', 'miktar', 'tarih', 'kullanici']
    readonly_fields = ['tarih']
    can_delete = False

@admin.register(StokHareket)
class StokHareketAdmin(admin.ModelAdmin):
    list_display = ['stok', 'tip', 'miktar', 'tarih', 'kullanici']
    list_filter = ['tip', 'tarih', 'stok__sube']
    search_fields = ['stok__ad', 'aciklama']
    readonly_fields = ['onceki_miktar', 'sonraki_miktar', 'tarih']
    list_per_page = 25

@admin.register(Recete)
class ReceteAdmin(admin.ModelAdmin):
    list_display = ['urun', 'stok_item', 'miktar']
    list_filter = ['urun__kategori', 'stok_item__sube']
    search_fields = ['urun__ad', 'stok_item__ad']
    list_per_page = 25

@admin.register(Tedarikci)
class TedarikciAdmin(admin.ModelAdmin):
    list_display = ['ad', 'yetkili', 'telefon', 'email', 'sube', 'aktif']
    list_filter = ['sube', 'aktif']
    search_fields = ['ad', 'yetkili', 'telefon', 'email', 'vergi_no']
    list_per_page = 25

# ==================== MASA VE MÜŞTERİ ====================
class AdisyonInline(admin.TabularInline):
    model = Adisyon
    extra = 0
    fields = ['id', 'siparis_turu', 'durum', 'toplam_tutar']
    readonly_fields = ['toplam_tutar']
    show_change_link = True
    can_delete = False
    
    def toplam_tutar(self, obj):
        if obj and obj.id:  # obj var mı kontrol et
            # DÜZELTİLDİ: format_html düzgün kullanılıyor
            return format_html('{} TL', obj.toplam_tutar())
        # DÜZELTİLDİ: Parametre eklendi
        return format_html('{}', '0 TL')
    toplam_tutar.short_description = 'Toplam'
    
    # İzinleri kısıtla
    def has_add_permission(self, request, obj=None):
        return False  # Yeni adisyon eklemeyi engelle

@admin.register(Masa)
class MasaAdmin(admin.ModelAdmin):
    list_display = ['masa_no', 'sube', 'kapasite', 'dolu_mu', 'durum_renkli', 'su_anki_tutar']
    list_filter = ['sube', 'dolu_mu', 'kapasite']
    search_fields = ['masa_no']
    list_editable = ['dolu_mu', 'kapasite']
    #inlines = [AdisyonInline]
    list_per_page = 25
    
    def durum_renkli(self, obj):
        if obj.dolu_mu:
            # DÜZELTİLDİ: Parametre eklendi
            return format_html('<span style="color: red; font-weight: bold;">{}</span>', '🔴 Dolu')
        # DÜZELTİLDİ: Parametre eklendi
        return format_html('<span style="color: green; font-weight: bold;">{}</span>', '🟢 Boş')
    durum_renkli.short_description = 'Durum'
    
    def su_anki_tutar(self, obj):
        tutar = obj.su_anki_tutar()
        if tutar > 0:
            # DÜZELTİLDİ: format_html düzgün kullanılıyor
            return format_html('<span style="color: blue; font-weight: bold;">{} TL</span>', tutar)
        # DÜZELTİLDİ: String yerine format_html ile döndür
        return format_html('{}', '-')
    su_anki_tutar.short_description = 'Güncel Tutar'

class RezervasyonInline(admin.TabularInline):
    model = Rezervasyon
    extra = 0
    fields = ['tarih', 'saat', 'kisi_sayisi', 'durum']
    show_change_link = True

class KisiselIndirimInline(admin.TabularInline):
    model = KisiselIndirim
    extra = 0
    fields = ['tip', 'deger', 'aktif', 'kullanilan', 'max_kullanim']

@admin.register(Musteri)
class MusteriAdmin(admin.ModelAdmin):
    list_display = ['ad_soyad', 'telefon', 'sadakat_seviyesi', 'sadakat_puani', 'toplam_harcama', 'ziyaret_sayisi']
    list_filter = ['sadakat_seviyesi', 'kayit_tarihi']
    search_fields = ['ad_soyad', 'telefon', 'email']
    readonly_fields = ['sadakat_puani', 'toplam_harcama', 'ziyaret_sayisi', 'son_ziyaret', 'kayit_tarihi']
    list_per_page = 25
    inlines = [RezervasyonInline, KisiselIndirimInline]

# ==================== ADİSYON VE SİPARİŞ ====================
class SiparisItemInline(admin.TabularInline):
    model = SiparisItem
    extra = 1
    fields = ['urun', 'adet', 'hazir_mi', 'ikram_mi', 'ozel_istek', 'toplam_fiyat']
    readonly_fields = ['toplam_fiyat']
    
    def toplam_fiyat(self, obj):
        if obj.id:
            return f"{obj.toplam_fiyat()} TL"
        return "0 TL"
    toplam_fiyat.short_description = 'Tutar'

@admin.register(Adisyon)
class AdisyonAdmin(admin.ModelAdmin):
    list_display = ['id', 'sube', 'masa', 'musteri', 'siparis_turu', 'durum', 'acilis_zamani', 'genel_toplam']
    list_filter = ['sube', 'siparis_turu', 'durum']
    search_fields = ['id', 'masa__masa_no', 'musteri__ad_soyad']
    readonly_fields = ['acilis_zamani', 'ara_toplam_hesap', 'genel_toplam']
    inlines = [SiparisItemInline]
    list_per_page = 25
    actions = ['adisyonu_kapat']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('sube', 'masa', 'musteri', 'siparis_turu', 'durum', 'paket_durumu', 'garson')
        }),
        ('Ödeme Bilgileri', {
            'fields': ('ara_toplam_hesap', 'indirim_tutari', 'indirim_kodu', 'genel_toplam', 'nakit_odenen', 'kart_odenen', 'odeme_turu')
        }),
    )
    
    def ara_toplam_hesap(self, obj):
        return f"{obj.ara_toplam()} TL"
    ara_toplam_hesap.short_description = 'Ara Toplam'
    
    def genel_toplam(self, obj):
        return f"{obj.toplam_tutar()} TL"
    genel_toplam.short_description = 'Genel Toplam'
    
    def adisyonu_kapat(self, request, queryset):
        queryset.update(durum='Kapali')
        self.message_user(request, f"{queryset.count()} adisyon kapatıldı.")
    adisyonu_kapat.short_description = "Seçili adisyonları kapat"

@admin.register(SiparisItem)
class SiparisItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'adisyon', 'urun', 'adet', 'hazir_mi', 'toplam_fiyat']
    list_filter = ['hazir_mi', 'ikram_mi']
    search_fields = ['urun__ad']
    list_per_page = 25

# ==================== REZERVASYON ====================
@admin.register(Rezervasyon)
class RezervasyonAdmin(admin.ModelAdmin):
    list_display = ['musteri_adi', 'tarih', 'saat', 'kisi_sayisi', 'masa', 'durum_renkli']
    list_filter = ['sube', 'durum', 'tarih']
    search_fields = ['musteri_adi', 'musteri_telefon']
    date_hierarchy = 'tarih'
    list_per_page = 25
    actions = ['rezervasyon_onayla', 'rezervasyon_iptal']
    
    def durum_renkli(self, obj):
        renkler = {
            'Bekliyor': 'orange',
            'Onaylandı': 'green',
            'İptal Edildi': 'red',
            'Tamamlandı': 'blue',
            'Gelmedi': 'gray',
        }
        # DÜZELTİLDİ: format_html düzgün kullanılıyor
        return format_html('<span style="color: {};">●</span> {}', renkler.get(obj.durum, 'black'), obj.durum)
    durum_renkli.short_description = 'Durum'
    
    def rezervasyon_onayla(self, request, queryset):
        queryset.update(durum='Onaylandı')
        self.message_user(request, f"{queryset.count()} rezervasyon onaylandı.")
    
    def rezervasyon_iptal(self, request, queryset):
        queryset.update(durum='İptal Edildi')
        self.message_user(request, f"{queryset.count()} rezervasyon iptal edildi.")

# ==================== İNDİRİM VE KUPON ====================
@admin.register(IndirimKuponu)
class IndirimKuponuAdmin(admin.ModelAdmin):
    list_display = ['kod', 'tip', 'deger', 'min_harcama', 'baslangic_tarihi', 'bitis_tarihi', 'durum_renkli']
    list_filter = ['tip', 'durum']
    search_fields = ['kod', 'aciklama']
    list_per_page = 25
    
    def durum_renkli(self, obj):
        renkler = {
            'aktif': 'green',
            'pasif': 'gray',
            'kullanildi': 'blue',
            'suresi_doldu': 'red',
        }
        # DÜZELTİLDİ: format_html düzgün kullanılıyor
        return format_html('<span style="color: {};">●</span> {}', renkler.get(obj.durum, 'black'), obj.get_durum_display())
    durum_renkli.short_description = 'Durum'

@admin.register(KuponKullanim)
class KuponKullanimAdmin(admin.ModelAdmin):
    list_display = ['kupon', 'musteri', 'indirim_tutari', 'kullanim_tarihi']
    list_filter = ['kullanim_tarihi']
    readonly_fields = ['kullanim_tarihi']

@admin.register(KisiselIndirim)
class KisiselIndirimAdmin(admin.ModelAdmin):
    list_display = ['musteri', 'tip', 'deger', 'aktif']
    list_filter = ['tip', 'aktif']
    search_fields = ['musteri__ad_soyad']

# ==================== DİĞER MODELLER ====================
@admin.register(Gider)
class GiderAdmin(admin.ModelAdmin):
    list_display = ['tarih', 'kategori', 'aciklama', 'tutar', 'sube']
    list_filter = ['kategori', 'sube']
    date_hierarchy = 'tarih'
    list_per_page = 25

@admin.register(IptalKaydi)
class IptalKaydiAdmin(admin.ModelAdmin):
    list_display = ['zaman', 'urun_adi', 'adet', 'tutar', 'garson']
    list_filter = ['zaman', 'sube']
    list_per_page = 25

@admin.register(GarsonCagri)
class GarsonCagriAdmin(admin.ModelAdmin):
    list_display = ['masa_no', 'sube', 'zaman', 'goruldu_mu']
    list_filter = ['sube', 'goruldu_mu']
    list_per_page = 25

@admin.register(KullaniciProfili)
class KullaniciProfiliAdmin(admin.ModelAdmin):
    list_display = ['user', 'rol', 'sube', 'aktif']
    list_filter = ['rol', 'sube', 'aktif']
    search_fields = ['user__username']


@admin.register(PersonelPuantaj)
class PersonelPuantajAdmin(admin.ModelAdmin):
    list_display = ['user', 'sube', 'tarih', 'giris_saati', 'cikis_saati']
    list_filter = ['sube', 'tarih']
    search_fields = ['user__username']
    list_per_page = 25


class MenuSiparisTalepKalemiInline(admin.TabularInline):
    model = MenuSiparisTalepKalemi
    extra = 0
    readonly_fields = ['urun', 'adet', 'ozel_istek']
    can_delete = False


@admin.register(MenuSiparisTalebi)
class MenuSiparisTalebiAdmin(admin.ModelAdmin):
    list_display = ['id', 'sube', 'masa_no', 'durum', 'olusturma_zamani', 'onaylayan', 'adisyon']
    list_filter = ['durum', 'sube', 'olusturma_zamani']
    search_fields = ['masa_no', 'sube__ad']
    inlines = [MenuSiparisTalepKalemiInline]
    list_per_page = 25

@admin.register(YedeklemeAyarlari)
class YedeklemeAyarlariAdmin(admin.ModelAdmin):
    list_display = ['yedekleme_tipi', 'zaman_araligi', 'aktif', 'son_yedekleme']
    list_filter = ['aktif']

@admin.register(YedekKaydi)
class YedekKaydiAdmin(admin.ModelAdmin):
    list_display = ['tarih', 'yedek_tipi', 'dosya_adi', 'durum']
    list_filter = ['durum']

# ==================== HIZLI SATIŞ ADMIN ====================

@admin.register(HizliSatisCihaz)
class HizliSatisCihazAdmin(admin.ModelAdmin):
    form = HizliSatisCihazAdminForm
    list_display = ['ad', 'sube', 'cihaz_tipi', 'baglanti_tipi', 'baglanti_hedefi_goster', 'seri_no', 'aktif']
    list_filter = ['sube', 'cihaz_tipi', 'baglanti_tipi', 'aktif']
    search_fields = ['ad', 'seri_no', 'ip_adresi', 'windows_yazici_adi']
    list_per_page = 25

    def baglanti_hedefi_goster(self, obj):
        return obj.baglanti_hedefi()
    baglanti_hedefi_goster.short_description = 'Baglanti'

@admin.register(HizliSatisKasa)
class HizliSatisKasaAdmin(admin.ModelAdmin):
    list_display = ['kasa_adi', 'kasa_no', 'sube', 'liste_sirasi', 'favori_bir', 'aktif', 'gunluk_ciro', 'gunluk_satis_sayisi']
    list_filter = ['sube', 'aktif', 'favori_bir']
    search_fields = ['kasa_adi', 'kasa_no']
    list_per_page = 25

@admin.register(HizliSatisKasaHareket)
class HizliSatisKasaHareketAdmin(admin.ModelAdmin):
    list_display = ['kasa', 'hareket_tipi', 'tutar', 'tarih', 'kullanici']
    list_filter = ['hareket_tipi', 'kasa__sube']
    readonly_fields = ['tarih']
    list_per_page = 25

@admin.register(HizliSatisUrun)
class HizliSatisUrunAdmin(admin.ModelAdmin):
    list_display = ['urun', 'sube', 'barkod', 'satis_fiyati', 'stok_miktari', 'stok_durumu', 'aktif']
    list_filter = ['sube', 'aktif', 'indirimde_mi']
    search_fields = ['urun__ad', 'barkod']
    list_editable = ['satis_fiyati', 'stok_miktari', 'aktif']
    list_per_page = 25
    
    def stok_durumu(self, obj):
        if obj.stok_miktari <= 0:
            # DÜZELTİLDİ: Parametre eklendi
            return format_html('<span style="color: red;">{}</span>', '🔴 Tükendi')
        elif obj.stok_miktari <= obj.kritik_stok:
            # DÜZELTİLDİ: Parametre eklendi
            return format_html('<span style="color: orange;">{}</span>', '🟡 Kritik')
        # DÜZELTİLDİ: Parametre eklendi
        return format_html('<span style="color: green;">{}</span>', '🟢 Normal')
    stok_durumu.short_description = "Stok Durumu"
    # stok_durumu.allow_tags = True  # BU SATIRI KALDIRIN, Django 6'da gerekli değil

@admin.register(HizliSatis)
class HizliSatisAdmin(admin.ModelAdmin):
    list_display = ['fis_no', 'kasa', 'tarih', 'toplam_tutar', 'odeme_tipi', 'kullanici']
    list_filter = ['kasa__sube', 'odeme_tipi', 'tarih']
    search_fields = ['fis_no', 'musteri__ad_soyad']
    date_hierarchy = 'tarih'
    readonly_fields = ['tarih', 'fis_no']
    list_per_page = 25
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('fis_no', 'kasa', 'sube', 'musteri', 'kullanici')
        }),
        ('Satış Bilgileri', {
            'fields': ('toplam_tutar', 'odeme_tipi', 'nakit_odenen', 'kart_odenen', 'para_ustu')
        }),
        ('Notlar', {
            'fields': ('notlar',),
            'classes': ('collapse',)
        }),
    )

@admin.register(HizliSatisItem)
class HizliSatisItemAdmin(admin.ModelAdmin):
    list_display = ['hizli_satis', 'urun', 'adet', 'birim_fiyat', 'toplam_fiyat', 'stok_dusuldu']
    list_filter = ['stok_dusuldu']
    search_fields = ['urun__ad', 'hizli_satis__fis_no']
    list_per_page = 25