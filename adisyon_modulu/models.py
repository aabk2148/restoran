from decimal import Decimal, ROUND_HALF_UP

from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings

from .module_control import default_enabled_module_ids

class Sube(models.Model):
    ad = models.CharField(max_length=100, verbose_name="Şube Adı")
    adres = models.TextField(blank=True, null=True)
    masa_plani_genislik = models.IntegerField(default=1200, verbose_name="Masa Planı Genişliği")
    masa_plani_yukseklik = models.IntegerField(default=800, verbose_name="Masa Planı Yüksekliği")
    kroki_arkaplan = models.ImageField(upload_to='krokiler/', blank=True, null=True, verbose_name="Kroki Arka Planı")

    class Meta:
        verbose_name = "Şube"
        verbose_name_plural = "Şubeler"

    def __str__(self):
        return self.ad


class Yazici(models.Model):
    BAGLANTI_TIPLERI = [
        ('ag', 'IP / Ag Yazicisi'),
        ('windows', 'Windows Yazicisi'),
    ]
    YAZICI_TIPLERI = [
        ('mutfak', 'Mutfak Yazıcısı'),
        ('kasa', 'Kasa Yazıcısı'),
    ]

    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='yazicilar')
    ad = models.CharField(max_length=50, verbose_name="Yazıcı Adı")
    baglanti_tipi = models.CharField(max_length=20, choices=BAGLANTI_TIPLERI, default='ag', verbose_name="Bağlantı Tipi")
    ip_adresi = models.GenericIPAddressField(verbose_name="Yazıcı IP", null=True, blank=True)
    port = models.IntegerField(default=9100)
    windows_yazici_adi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Windows Yazıcı Adı")
    yazici_tipi = models.CharField(max_length=10, choices=YAZICI_TIPLERI, default='mutfak', verbose_name="Yazıcı Tipi")

    class Meta:
        verbose_name = "Yazıcı"
        verbose_name_plural = "Yazıcılar"

    def __str__(self):
        return f"{self.sube.ad} - {self.ad} ({self.get_yazici_tipi_display()})"

    def baglanti_hedefi(self):
        if self.baglanti_tipi == 'windows':
            return self.windows_yazici_adi or self.ad
        return f"{self.ip_adresi}:{self.port}"


class Bolge(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='bolgeler')
    ad = models.CharField(max_length=50, verbose_name="Bölge Adı")
    yazici = models.ForeignKey(Yazici, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Bölge"
        verbose_name_plural = "Bölgeler"

    def __str__(self):
        return f"{self.sube.ad} - {self.ad}"


class Kategori(models.Model):
    ad = models.CharField(max_length=50, verbose_name="Kategori Adı")
    sira = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sira']
        verbose_name = "Kategori"
        verbose_name_plural = "Kategoriler"

    def __str__(self):
        return self.ad


class Urun(models.Model):
    KDV_CHOICES = [(1, '%1'), (10, '%10'), (20, '%20')]

    kategori = models.ForeignKey(
        Kategori,
        on_delete=models.CASCADE,
        related_name='urunler',
        null=True,
        blank=True
    )
    sira = models.PositiveIntegerField(default=0, verbose_name="Sıra")
    ad = models.CharField(max_length=100, verbose_name="Ürün Adı")
    fiyat = models.DecimalField(max_digits=10, decimal_places=2)
    kdv_orani = models.IntegerField(choices=KDV_CHOICES, default=10)
    gorsel = models.ImageField(upload_to='urunler/', blank=True, null=True)
    bolge = models.ForeignKey(Bolge, on_delete=models.SET_NULL, null=True, blank=True)
    aciklama = models.TextField(blank=True, null=True)
    alerjen_bilgisi = models.TextField(blank=True, null=True)
    stok_kalemi = models.ForeignKey(
        'StokKalemi',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='urunler',
        verbose_name="Bağlı Stok Kalemi"
    )
    receteli_mi = models.BooleanField("Reçeteli ürün mü?", default=False)
    alerjenler = models.ManyToManyField(
        'Alerjen',
        blank=True,
        related_name='urunler',
        verbose_name='Alerjenler'
    )

    alerjenler = models.ManyToManyField(
        'Alerjen',
        blank=True,
        related_name='urunler',
        verbose_name='Alerjenler'
    )

    class Meta:
        ordering = ['sira', 'ad']
        verbose_name = "Ürün"
        verbose_name_plural = "Ürünler"

    def __str__(self):
        return f"[{self.kategori}] {self.ad}" if self.kategori else self.ad


class Alerjen(models.Model):
    ad = models.CharField(max_length=100, unique=True, verbose_name="Alerjen Adı")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")

    class Meta:
        verbose_name = "Alerjen"
        verbose_name_plural = "Alerjenler"
        ordering = ["ad"]

    def __str__(self):
        return self.ad


class Masa(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='masalar')
    masa_no = models.CharField(max_length=10)
    dolu_mu = models.BooleanField(default=False)
    kapasite = models.IntegerField(default=4, help_text="Masa kapasitesi (kişi sayısı)")
    pos_x = models.FloatField(default=0, help_text="X Koordinatı")
    pos_y = models.FloatField(default=0, help_text="Y Koordinatı")
    genislik = models.FloatField(default=120, help_text="Masa Genişliği")
    yukseklik = models.FloatField(default=120, help_text="Masa Yüksekliği")

    class Meta:
        verbose_name = "Masa"
        verbose_name_plural = "Masalar"

    def __str__(self):
        return f"{self.sube.ad} - Masa {self.masa_no}"

    def su_anki_tutar(self):
        adisyon = self.adisyon_set.filter(durum='Acik').first()
        return adisyon.toplam_tutar() if adisyon else 0

    def save(self, *args, **kwargs):
        if self._state.adding and self.pos_x == 0 and self.pos_y == 0 and self.sube_id:
            self.pos_x, self.pos_y = self._varsayilan_konum_hesapla()
        super().save(*args, **kwargs)

    def _varsayilan_konum_hesapla(self):
        plan_genislik = max(int(getattr(self.sube, 'masa_plani_genislik', 1200) or 1200), 360)
        plan_yukseklik = max(int(getattr(self.sube, 'masa_plani_yukseklik', 800) or 800), 300)
        masa_genislik = max(float(self.genislik or 120), 80)
        masa_yukseklik = max(float(self.yukseklik or 120), 80)
        bosluk_x = 32
        bosluk_y = 28
        kenar_boslugu = 32

        kullanilabilir_genislik = max(plan_genislik - (kenar_boslugu * 2), masa_genislik)
        kolon_sayisi = max(
            1,
            int((kullanilabilir_genislik + bosluk_x) // (masa_genislik + bosluk_x))
        )

        mevcut_sayi = Masa.objects.filter(sube_id=self.sube_id).count()
        satir = mevcut_sayi // kolon_sayisi
        sutun = mevcut_sayi % kolon_sayisi

        x = kenar_boslugu + sutun * (masa_genislik + bosluk_x)
        y = kenar_boslugu + satir * (masa_yukseklik + bosluk_y)

        max_x = max(kenar_boslugu, plan_genislik - masa_genislik - kenar_boslugu)
        max_y = max(kenar_boslugu, plan_yukseklik - masa_yukseklik - kenar_boslugu)
        return min(x, max_x), min(y, max_y)


class Musteri(models.Model):
    ad_soyad = models.CharField(max_length=100)
    telefon = models.CharField(max_length=15, unique=True)
    adres = models.TextField()
    kayit_tarihi = models.DateTimeField(auto_now_add=True)

    email = models.EmailField(blank=True, null=True, verbose_name="E-posta")
    dogum_tarihi = models.DateField(blank=True, null=True, verbose_name="Doğum Tarihi")
    cinsiyet = models.CharField(max_length=10, choices=[('E', 'Erkek'), ('K', 'Kadın')], blank=True, null=True)

    sadakat_puani = models.IntegerField(default=0, verbose_name="Sadakat Puanı")
    toplam_harcama = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Toplam Harcama")
    ziyaret_sayisi = models.IntegerField(default=0, verbose_name="Ziyaret Sayısı")
    son_ziyaret = models.DateTimeField(blank=True, null=True, verbose_name="Son Ziyaret")

    SADAKAT_SEVIYESI = [
        ('Bronz', 'Bronz'),
        ('Gümüş', 'Gümüş'),
        ('Altın', 'Altın'),
        ('Platin', 'Platin'),
    ]
    sadakat_seviyesi = models.CharField(max_length=10, choices=SADAKAT_SEVIYESI, default='Bronz', verbose_name="Sadakat Seviyesi")

    class Meta:
        verbose_name = "Müşteri"
        verbose_name_plural = "Müşteriler"

    def __str__(self):
        return self.ad_soyad

    def puan_ekle(self, harcama_tutari):
        kazanilan_puan = int(harcama_tutari / 10)
        self.sadakat_puani += kazanilan_puan
        self.toplam_harcama += harcama_tutari
        self.ziyaret_sayisi += 1
        self.son_ziyaret = timezone.now()
        self.seviye_guncelle()
        self.save()
        return kazanilan_puan

    def seviye_guncelle(self):
        if self.toplam_harcama >= 10000:
            self.sadakat_seviyesi = 'Platin'
        elif self.toplam_harcama >= 5000:
            self.sadakat_seviyesi = 'Altın'
        elif self.toplam_harcama >= 1000:
            self.sadakat_seviyesi = 'Gümüş'
        else:
            self.sadakat_seviyesi = 'Bronz'

    def dogum_gunu_indirimi(self):
        if self.dogum_tarihi:
            bugun = timezone.now().date()
            if self.dogum_tarihi.month == bugun.month and self.dogum_tarihi.day == bugun.day:
                return 20
        return 0


class Adisyon(models.Model):
    SIPARIS_TURU_CHOICES = [('Masa', 'Masa'), ('Paket', 'Paket')]
    DURUM_CHOICES = [('Acik', 'Açık'), ('Kapali', 'Kapalı')]
    PAKET_DURUMU_CHOICES = [
        ('Hazirlaniyor', 'Hazırlanıyor'),
        ('Yolda', 'Yolda'),
        ('Teslim Edildi', 'Teslim Edildi')
    ]

    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, null=True, blank=True)
    masa = models.ForeignKey(Masa, on_delete=models.CASCADE, null=True, blank=True)
    musteri = models.ForeignKey(Musteri, on_delete=models.SET_NULL, null=True, blank=True)
    siparis_turu = models.CharField(max_length=10, choices=SIPARIS_TURU_CHOICES, default='Masa')
    durum = models.CharField(max_length=10, choices=DURUM_CHOICES, default='Acik')
    paket_durumu = models.CharField(max_length=20, choices=PAKET_DURUMU_CHOICES, blank=True, null=True)
    acilis_zamani = models.DateTimeField(auto_now_add=True)
    indirim_tutari = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    indirim_kodu = models.CharField(max_length=50, blank=True, null=True, verbose_name="İndirim Kodu")
    nakit_odenen = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    kart_odenen = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    odeme_turu = models.CharField(max_length=20, blank=True, null=True)
    garson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Hesabı Kesen Garson")

    class Meta:
        verbose_name = "Adisyon"
        verbose_name_plural = "Adisyonlar"

    def ara_toplam(self):
        return sum(item.toplam_fiyat() for item in self.siparisler.all())

    def toplam_tutar(self):
        tutar = self.ara_toplam() - self.indirim_tutari
        return tutar if tutar > 0 else 0


class SiparisItem(models.Model):
    adisyon = models.ForeignKey(Adisyon, related_name='siparisler', on_delete=models.CASCADE)
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE)
    adet = models.PositiveIntegerField(default=1)
    siparisi_alan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='aldigi_siparisler', verbose_name="Siparisi Alan")
    hazir_mi = models.BooleanField(default=False)
    ikram_mi = models.BooleanField(default=False)
    yazdirildi = models.BooleanField(default=False)
    bildirim_gosterildi = models.BooleanField(default=False)
    iptal_edildi = models.BooleanField(default=False)
    ozel_istek = models.TextField(blank=True, null=True, verbose_name="Özel İstek")
    stok_dusuldu = models.BooleanField(default=False, verbose_name="Stok Düşüldü mü?")
    eklenme_zamani = models.DateTimeField(auto_now_add=True, null=True, verbose_name="Sipariş Verilme Zamanı")
    hazir_olma_zamani = models.DateTimeField(null=True, blank=True, verbose_name="Hazır İşaretlenme Zamanı")

    son_siparis_hareketi = models.DateTimeField(null=True, blank=True, verbose_name="Son Siparis Hareketi")

    def toplam_fiyat(self):
        return 0 if self.ikram_mi else self.urun.fiyat * self.adet


class SiparisNotlari(models.Model):
    siparis_item = models.ForeignKey(SiparisItem, on_delete=models.CASCADE, related_name='notlar')
    not_metni = models.TextField(verbose_name="Not")
    eklenme_zamani = models.DateTimeField(auto_now_add=True)
    ekleyen = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Sipariş Notu"
        verbose_name_plural = "Sipariş Notları"
        ordering = ['eklenme_zamani']

    def __str__(self):
        return f"{self.siparis_item.urun.ad} - {self.not_metni[:50]}"


class Tedarikci(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='tedarikciler')
    ad = models.CharField(max_length=100, verbose_name="Tedarikçi Adı")
    yetkili = models.CharField(max_length=100, verbose_name="Yetkili Kişi")
    telefon = models.CharField(max_length=15, verbose_name="Telefon")
    email = models.EmailField(verbose_name="E-posta")
    adres = models.TextField(blank=True, null=True, verbose_name="Adres")
    vergi_no = models.CharField(max_length=20, blank=True, null=True, verbose_name="Vergi No")
    notlar = models.TextField(blank=True, null=True, verbose_name="Notlar")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    kayit_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Tedarikçi"
        verbose_name_plural = "Tedarikçiler"

    def __str__(self):
        return f"{self.ad} - {self.yetkili}"


class StokKalemi(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='stok_kalemleri')
    ad = models.CharField(max_length=100, verbose_name="Stok Adı")
    miktar = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    birim = models.CharField(
        max_length=10,
        choices=[('kg', 'kg'), ('lt', 'lt'), ('adet', 'adet'), ('gr', 'gr')],
        default='kg'
    )
    kritik_seviye = models.DecimalField(max_digits=10, decimal_places=3, default=1)
    tedarikci = models.ForeignKey(
        Tedarikci,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Tedarikçi"
    )
    fiyat = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Birim Fiyat")
    barkod = models.CharField(max_length=50, blank=True, null=True, verbose_name="Barkod")

    # YENİ EKLENEN ALANLAR
    satilabilir_mi = models.BooleanField("Direkt satılabilir mi?", default=False)
    uretimde_kullanilir_mi = models.BooleanField("Üretimde kullanılır mı?", default=True)
    otomatik_urun_olustur = models.BooleanField("Otomatik ürün oluştur", default=False)

    # ORİJİNAL ALANLAR KALMALI
    son_kullanim_tarihi = models.DateField(blank=True, null=True, verbose_name="Son Kullanma Tarihi")
    uyari_verildi = models.BooleanField(default=False, verbose_name="Kritik Uyarısı Verildi mi?")
    uyari_tarihi = models.DateTimeField(blank=True, null=True, verbose_name="Son Uyarı Tarihi")

    class Meta:
        verbose_name = "Stok Kalemi"
        verbose_name_plural = "Stok Kalemleri"

    def __str__(self):
        return f"{self.sube.ad} - {self.ad}"

    def miktar_guncelle(self, yeni_miktar, tip, kullanici=None, siparis_item=None, aciklama=""):
        onceki = self.miktar
        fark = yeni_miktar - onceki

        self.miktar = yeni_miktar
        self.save()

        if fark > 0 and self.miktar > self.kritik_seviye:
            self.uyari_verildi = False
            self.save()

        StokHareket.objects.create(
            stok=self,
            tip=tip,
            miktar=fark,
            onceki_miktar=onceki,
            sonraki_miktar=yeni_miktar,
            aciklama=aciklama,
            siparis_item=siparis_item,
            kullanici=kullanici
        )

        return fark

class StokHareket(models.Model):
    HAREKET_TIPI = [
        ('giris', 'Stok Girişi'),
        ('cikis', 'Stok Çıkışı'),
        ('sayim', 'Sayım Düzeltmesi'),
        ('fire', 'Fire'),
    ]

    stok = models.ForeignKey(StokKalemi, on_delete=models.CASCADE, related_name='hareketler')
    tip = models.CharField(max_length=10, choices=HAREKET_TIPI, verbose_name="Hareket Tipi")
    miktar = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Miktar")
    onceki_miktar = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Önceki Miktar")
    sonraki_miktar = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Sonraki Miktar")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")

    siparis_item = models.ForeignKey(SiparisItem, on_delete=models.SET_NULL, null=True, blank=True)
    kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    tarih = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Stok Hareketi"
        verbose_name_plural = "Stok Hareketleri"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.stok.ad} - {self.get_tip_display()} - {self.miktar} {self.stok.birim}"


class Recete(models.Model):
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE, related_name='receteler')
    stok_item = models.ForeignKey(StokKalemi, on_delete=models.CASCADE)
    miktar = models.DecimalField(max_digits=10, decimal_places=3)


class IptalKaydi(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE)
    urun_adi = models.CharField(max_length=100)
    adet = models.PositiveIntegerField()
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    garson = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    sebep = models.TextField()
    zaman = models.DateTimeField(auto_now_add=True)


class GarsonCagri(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE)
    masa_no = models.CharField(max_length=10)
    zaman = models.DateTimeField(auto_now_add=True)

    goruldu_mu = models.BooleanField(default=False)
    tamamlandi_mi = models.BooleanField(default=False)  # YENİ


class Gider(models.Model):
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE)
    kategori = models.CharField(max_length=50)
    aciklama = models.CharField(max_length=200)
    sorumlu = models.CharField(max_length=100, blank=True, null=True)
    tutar = models.DecimalField(max_digits=10, decimal_places=2)
    tarih = models.DateField(default=timezone.now)

    class Meta:
        verbose_name = "Gider"
        verbose_name_plural = "Giderler"


class KullaniciProfili(models.Model):
    ROL_SECENEKLERI = [
        ('Yonetici', 'Yönetici'),
        ('Garson', 'Garson'),
        ('Asci', 'Aşçı'),
        ('Kasa', 'Kasa Personeli'),
        ('Muhasebe', 'Muhasebe'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profil')
    rol = models.CharField(max_length=20, choices=ROL_SECENEKLERI, default='Garson')
    sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True)
    telefon = models.CharField(max_length=15, blank=True, null=True)
    ise_baslama_tarihi = models.DateField(default=timezone.now)
    aktif = models.BooleanField(default=True)
    kvkk_onaylandi = models.BooleanField(default=False, verbose_name="KVKK Onaylandi")
    kvkk_onay_tarihi = models.DateTimeField(null=True, blank=True, verbose_name="KVKK Onay Tarihi")
    yonetim_paneli_modulleri = models.JSONField(
        null=True,
        blank=True,
        default=None,
        verbose_name="Yonetim Paneli Modulleri",
        help_text="Bos birakilirsa kullanici rolune uygun tum paneller gorunur.",
    )

    class Meta:
        verbose_name = "Kullanıcı Profili"
        verbose_name_plural = "Kullanıcı Profilleri"

    def __str__(self):
        return f"{self.user.username} - {self.get_rol_display()}"


class ModulAyari(models.Model):
    aktif_moduller = models.JSONField(
        default=default_enabled_module_ids,
        blank=True,
        verbose_name="Kullanima Acik Moduller",
        help_text="Secili moduller uygulamada erisilebilir olur. Kapali moduller kodda dursa da kullanicilar ulasamaz.",
    )
    guncellenme_zamani = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Modul Ayari"
        verbose_name_plural = "Modul Ayarlari"

    def __str__(self):
        return "Genel Modul Ayarlari"


class PersonelPuantaj(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='puantaj_kayitlari')
    sube = models.ForeignKey(Sube, on_delete=models.SET_NULL, null=True, blank=True, related_name='puantaj_kayitlari')
    tarih = models.DateField(default=timezone.localdate)
    giris_saati = models.DateTimeField(default=timezone.now)
    cikis_saati = models.DateTimeField(null=True, blank=True)
    notu = models.TextField(blank=True, null=True, verbose_name="Not")

    class Meta:
        verbose_name = "Personel Puantaj"
        verbose_name_plural = "Personel Puantajlari"
        ordering = ['-giris_saati']

    def __str__(self):
        return f"{self.user.username} - {self.tarih}"

    @property
    def aktif_mi(self):
        return self.cikis_saati is None

    @property
    def toplam_sure_dakika(self):
        bitis = self.cikis_saati or timezone.now()
        return max(int((bitis - self.giris_saati).total_seconds() // 60), 0)


class MenuSiparisTalebi(models.Model):
    DURUM_SECENEKLERI = [
        ('Beklemede', 'Beklemede'),
        ('Onaylandi', 'Onaylandi'),
        ('Reddedildi', 'Reddedildi'),
    ]

    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='menu_siparis_talepleri')
    masa = models.ForeignKey(Masa, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_siparis_talepleri')
    masa_no = models.CharField(max_length=20, verbose_name="Masa No")
    durum = models.CharField(max_length=15, choices=DURUM_SECENEKLERI, default='Beklemede')
    musteri_notu = models.TextField(blank=True, null=True, verbose_name="Musteri Notu")
    olusturma_zamani = models.DateTimeField(auto_now_add=True)
    guncelleme_zamani = models.DateTimeField(auto_now=True)
    onaylayan = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='onaylanan_menu_siparis_talepleri'
    )
    onay_zamani = models.DateTimeField(null=True, blank=True)
    red_sebebi = models.TextField(blank=True, null=True, verbose_name="Red Sebebi")
    olusturan_ip = models.GenericIPAddressField(null=True, blank=True)
    adisyon = models.ForeignKey(Adisyon, on_delete=models.SET_NULL, null=True, blank=True, related_name='menu_talepleri')

    class Meta:
        verbose_name = "Menu Siparis Talebi"
        verbose_name_plural = "Menu Siparis Talepleri"
        ordering = ['-olusturma_zamani']

    def __str__(self):
        return f"{self.sube.ad} / Masa {self.masa_no} / {self.get_durum_display()}"

    def toplam_tutar(self):
        return sum(kalem.toplam_fiyat() for kalem in self.kalemler.all())


class MenuSiparisTalepKalemi(models.Model):
    talep = models.ForeignKey(MenuSiparisTalebi, on_delete=models.CASCADE, related_name='kalemler')
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE)
    adet = models.PositiveIntegerField(default=1)
    ozel_istek = models.TextField(blank=True, null=True, verbose_name="Ozel Istek")

    class Meta:
        verbose_name = "Menu Siparis Kalemi"
        verbose_name_plural = "Menu Siparis Kalemleri"

    def __str__(self):
        return f"{self.urun.ad} x{self.adet}"

    def toplam_fiyat(self):
        return self.urun.fiyat * self.adet


class Rezervasyon(models.Model):
    DURUMLAR = [
        ('Bekliyor', 'Bekliyor'),
        ('Onaylandı', 'Onaylandı'),
        ('İptal Edildi', 'İptal Edildi'),
        ('Tamamlandı', 'Tamamlandı'),
        ('Gelmedi', 'Gelmedi'),
    ]

    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='rezervasyonlar')
    musteri = models.ForeignKey(Musteri, on_delete=models.CASCADE, null=True, blank=True)
    musteri_adi = models.CharField(max_length=100)
    musteri_telefon = models.CharField(max_length=20)
    musteri_email = models.EmailField(blank=True, null=True)
    musteri_notu = models.TextField(blank=True)

    masa = models.ForeignKey(Masa, on_delete=models.SET_NULL, null=True, blank=True)
    kisi_sayisi = models.IntegerField()
    tarih = models.DateField()
    saat = models.TimeField()
    sure = models.IntegerField(default=120, help_text="Dakika cinsinden rezervasyon süresi")

    durum = models.CharField(max_length=20, choices=DURUMLAR, default='Bekliyor')

    olusturma_zamani = models.DateTimeField(auto_now_add=True)
    guncelleme_zamani = models.DateTimeField(auto_now=True)
    olusturan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    ozel_istek = models.TextField(blank=True, help_text="Özel gün, alerji, not vb.")
    hatirlatma_gonderildi = models.BooleanField(default=False)

    masa_kilitli = models.BooleanField(default=False, help_text="Rezervasyon için masa kilitli mi?")
    kilit_baslangic = models.DateTimeField(null=True, blank=True, help_text="Masanın kilitlendiği zaman")
    kilit_bitis = models.DateTimeField(null=True, blank=True, help_text="Masanın kilidinin açılacağı zaman")
    hatirlatma_yapildi = models.BooleanField(default=False)

    class Meta:
        ordering = ['tarih', 'saat']
        verbose_name = "Rezervasyon"
        verbose_name_plural = "Rezervasyonlar"

    def __str__(self):
        return f"{self.musteri_adi} - {self.tarih} {self.saat} ({self.kisi_sayisi} kişi)"

    @property
    def bitis_saati(self):
        from datetime import datetime, timedelta
        bitis = datetime.combine(self.tarih, self.saat) + timedelta(minutes=self.sure)
        return bitis.time()

    def masa_kilitlenebilir_mi(self):
        if not self.masa:
            return False, "Masa seçilmemiş"

        if self.masa.dolu_mu:
            return False, "Masa şu anda dolu"

        from datetime import datetime, timedelta

        if isinstance(self.tarih, str):
            tarih_obj = datetime.strptime(self.tarih, '%Y-%m-%d').date()
        else:
            tarih_obj = self.tarih

        if isinstance(self.saat, str):
            saat_obj = datetime.strptime(self.saat, '%H:%M').time()
        else:
            saat_obj = self.saat

        rez_baslangic = datetime.combine(tarih_obj, saat_obj)
        rez_bitis = rez_baslangic + timedelta(minutes=self.sure)

        cakisan = Rezervasyon.objects.filter(
            masa=self.masa,
            tarih=self.tarih,
            durum__in=['Onaylandı', 'Bekliyor']
        ).exclude(id=self.id)

        for rez in cakisan:
            if isinstance(rez.tarih, str):
                rez_tarih_obj = datetime.strptime(rez.tarih, '%Y-%m-%d').date()
            else:
                rez_tarih_obj = rez.tarih

            if isinstance(rez.saat, str):
                rez_saat_obj = datetime.strptime(rez.saat, '%H:%M').time()
            else:
                rez_saat_obj = rez.saat

            rez_bas = datetime.combine(rez_tarih_obj, rez_saat_obj)
            rez_bit = rez_bas + timedelta(minutes=rez.sure)

            if rez_bas < rez_bitis and rez_bit > rez_baslangic:
                return False, f"Masa {rez.saat} - {rez.bitis_saati} arasında dolu"

        return True, "Masa kilitlenebilir"

    def masa_kilit(self):
        from django.utils import timezone
        from datetime import datetime, timedelta
        import pytz

        kontrol, mesaj = self.masa_kilitlenebilir_mi()

        if kontrol:
            turkey_tz = pytz.timezone('Europe/Istanbul')

            if isinstance(self.tarih, str):
                tarih_obj = datetime.strptime(self.tarih, '%Y-%m-%d').date()
            else:
                tarih_obj = self.tarih

            if isinstance(self.saat, str):
                saat_obj = datetime.strptime(self.saat, '%H:%M').time()
            else:
                saat_obj = self.saat

            rezervasyon_datetime = datetime.combine(tarih_obj, saat_obj)
            rezervasyon_datetime = turkey_tz.localize(rezervasyon_datetime)

            simdi = timezone.localtime(timezone.now())

            kilit_baslangic = rezervasyon_datetime - timedelta(minutes=30)
            kilit_bitis = rezervasyon_datetime + timedelta(minutes=self.sure)

            self.kilit_baslangic = kilit_baslangic
            self.kilit_bitis = kilit_bitis

            if simdi >= kilit_baslangic:
                self.masa_kilitli = True
                self.save()
                return True, "Masa hemen kilitlendi"
            else:
                self.masa_kilitli = False
                self.save()
                dakika_fark = int((kilit_baslangic - simdi).total_seconds() / 60)
                return True, f"Masa {dakika_fark} dakika sonra kilitlenecek"

        return False, mesaj

    def masa_kilit_kontrol(self):
        from django.utils import timezone
        if not self.masa_kilitli or not self.kilit_bitis:
            return False
        return timezone.now() < self.kilit_bitis


class YedeklemeAyarlari(models.Model):
    YEDEKLEME_TIPI = [
        ('yerel', 'Yerel Disk'),
        ('google_drive', 'Google Drive'),
        ('dropbox', 'Dropbox'),
    ]

    ZAMAN_ARALIGI = [
        (1, 'Her gün'),
        (7, 'Haftada bir'),
        (30, 'Ayda bir'),
    ]

    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    yedekleme_tipi = models.CharField(max_length=20, choices=YEDEKLEME_TIPI, default='yerel', verbose_name="Yedekleme Tipi")
    zaman_araligi = models.IntegerField(choices=ZAMAN_ARALIGI, default=1, verbose_name="Yedekleme Sıklığı")
    yedekleme_saati = models.TimeField(default='03:00', verbose_name="Yedekleme Saati")
    son_yedekleme = models.DateTimeField(null=True, blank=True, verbose_name="Son Yedekleme")

    yerel_klasor = models.CharField(max_length=255, default='C:\\RestoranYedek', verbose_name="Yerel Klasör Yolu")
    max_yerel_yedek = models.IntegerField(default=10, verbose_name="Yerelde Tutulacak Yedek Sayısı")

    bulut_access_token = models.TextField(blank=True, null=True)
    bulut_refresh_token = models.TextField(blank=True, null=True)
    bulut_klasor = models.CharField(max_length=255, default='RestoranYedek', verbose_name="Bulut Klasör Adı")

    class Meta:
        verbose_name = "Yedekleme Ayarı"
        verbose_name_plural = "Yedekleme Ayarları"

    def __str__(self):
        return f"{self.get_yedekleme_tipi_display()} - {self.get_zaman_araligi_display()}"


class YedekKaydi(models.Model):
    DURUMLAR = [
        ('basari', 'Başarılı'),
        ('basarisiz', 'Başarısız'),
        ('isleniyor', 'İşleniyor'),
    ]

    tarih = models.DateTimeField(auto_now_add=True)
    yedek_tipi = models.CharField(max_length=20, choices=YedeklemeAyarlari.YEDEKLEME_TIPI, verbose_name="Yedek Tipi")
    dosya_adi = models.CharField(max_length=255, verbose_name="Dosya Adı")
    dosya_boyutu = models.CharField(max_length=50, blank=True, null=True, verbose_name="Dosya Boyutu")
    durum = models.CharField(max_length=20, choices=DURUMLAR, default='isleniyor')
    hata_mesaji = models.TextField(blank=True, null=True)
    aciklama = models.CharField(max_length=255, blank=True, null=True, verbose_name="Açıklama")

    class Meta:
        verbose_name = "Yedek Kaydı"
        verbose_name_plural = "Yedek Kayıtları"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.tarih.strftime('%d.%m.%Y %H:%M')} - {self.dosya_adi}"


class IndirimKuponu(models.Model):
    KUPON_TIPI = [
        ('yuzde', 'Yüzde İndirimi'),
        ('sabit', 'Sabit Tutar'),
        ('puan', 'Puan Kullanımı'),
    ]

    DURUMLAR = [
        ('aktif', 'Aktif'),
        ('pasif', 'Pasif'),
        ('kullanildi', 'Kullanıldı'),
        ('suresi_doldu', 'Süresi Doldu'),
    ]

    kod = models.CharField(max_length=50, unique=True, verbose_name="Kupon Kodu")
    tip = models.CharField(max_length=10, choices=KUPON_TIPI, verbose_name="Kupon Tipi")
    deger = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Değer")
    aciklama = models.CharField(max_length=200, verbose_name="Açıklama")

    min_harcama = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Minimum Harcama")
    gerekli_puan = models.IntegerField(default=0, verbose_name="Gerekli Puan")

    baslangic_tarihi = models.DateField(verbose_name="Başlangıç Tarihi")
    bitis_tarihi = models.DateField(verbose_name="Bitiş Tarihi")

    max_kullanim = models.IntegerField(default=1, verbose_name="Maksimum Kullanım")
    kullanilan = models.IntegerField(default=0, verbose_name="Kullanılan")

    musteri_bazli = models.BooleanField(default=True, verbose_name="Müşteri bazlı?")
    uygun_seviyeler = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Virgülle ayırın: Bronz,Gümüş,Altın,Platin"
    )

    durum = models.CharField(max_length=20, choices=DURUMLAR, default='aktif', verbose_name="Durum")

    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    olusturan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "İndirim Kuponu"
        verbose_name_plural = "İndirim Kuponları"
        ordering = ['-olusturma_tarihi']

    def __str__(self):
        return f"{self.kod} - {self.get_tip_display()} ({self.deger})"

    def kullanilabilir_mi(self, musteri, harcama_tutari):
        bugun = timezone.now().date()

        if self.durum != 'aktif':
            return False, "Kupon aktif değil"

        if bugun < self.baslangic_tarihi or bugun > self.bitis_tarihi:
            return False, "Kupon süresi dolmuş"

        if self.kullanilan >= self.max_kullanim:
            return False, "Kupon kullanım limiti dolmuş"

        if harcama_tutari < self.min_harcama:
            return False, f"Minimum {self.min_harcama} TL harcama gerekli"

        if self.uygun_seviyeler and musteri:
            seviyeler = [s.strip() for s in self.uygun_seviyeler.split(',')]
            if musteri.sadakat_seviyesi not in seviyeler:
                return False, "Bu kupon seviyeniz için geçerli değil"

        if self.tip == 'puan' and musteri and musteri.sadakat_puani < self.gerekli_puan:
            return False, f"Yetersiz puan. Gerekli: {self.gerekli_puan}"

        return True, "Kullanılabilir"

    def kullan(self, musteri, adisyon):
        kontrol, mesaj = self.kullanilabilir_mi(musteri, adisyon.ara_toplam())

        if not kontrol:
            return False, mesaj

        if self.tip == 'yuzde':
            indirim = adisyon.ara_toplam() * self.deger / 100
        elif self.tip == 'sabit':
            indirim = self.deger
        else:
            indirim = self.deger
            musteri.sadakat_puani -= self.gerekli_puan
            musteri.save()

        adisyon.indirim_tutari += indirim
        adisyon.indirim_kodu = self.kod
        adisyon.save()

        self.kullanilan += 1
        if self.kullanilan >= self.max_kullanim:
            self.durum = 'kullanildi'
        self.save()

        return True, f"{indirim:.2f} TL indirim uygulandı"


class KuponKullanim(models.Model):
    kupon = models.ForeignKey(IndirimKuponu, on_delete=models.CASCADE, related_name='kullanimlar')
    musteri = models.ForeignKey(Musteri, on_delete=models.CASCADE)
    adisyon = models.ForeignKey(Adisyon, on_delete=models.CASCADE)
    indirim_tutari = models.DecimalField(max_digits=10, decimal_places=2)
    kullanim_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Kupon Kullanımı"
        verbose_name_plural = "Kupon Kullanımları"
        ordering = ['-kullanim_tarihi']

    def __str__(self):
        return f"{self.kupon.kod} - {self.musteri.ad_soyad} - {self.kullanim_tarihi}"


class KisiselIndirim(models.Model):
    INDIRIM_TIPI = [
        ('yuzde', 'Yüzde İndirimi'),
        ('sabit', 'Sabit Tutar'),
    ]

    musteri = models.ForeignKey(Musteri, on_delete=models.CASCADE, related_name='kisisel_indirimler')
    tip = models.CharField(max_length=10, choices=INDIRIM_TIPI, verbose_name="İndirim Tipi")
    deger = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="İndirim Değeri")
    aciklama = models.CharField(max_length=200, verbose_name="Açıklama")

    min_harcama = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Minimum Harcama")
    max_kullanim = models.IntegerField(default=0, verbose_name="Maksimum Kullanım (0=sınırsız)")
    kullanilan = models.IntegerField(default=0, verbose_name="Kullanılan")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")

    baslangic_tarihi = models.DateField(null=True, blank=True, verbose_name="Başlangıç Tarihi")
    bitis_tarihi = models.DateField(null=True, blank=True, verbose_name="Bitiş Tarihi")

    olusturma_tarihi = models.DateTimeField(auto_now_add=True)
    olusturan = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = "Kişisel İndirim"
        verbose_name_plural = "Kişisel İndirimler"
        ordering = ['-olusturma_tarihi']

    def __str__(self):
        return f"{self.musteri.ad_soyad} - {self.get_tip_display()} ({self.deger})"

    def kullanilabilir_mi(self, harcama_tutari):
        if not self.aktif:
            return False, "İndirim aktif değil"

        bugun = timezone.now().date()
        if self.baslangic_tarihi and bugun < self.baslangic_tarihi:
            return False, "İndirim henüz başlamadı"
        if self.bitis_tarihi and bugun > self.bitis_tarihi:
            return False, "İndirim süresi dolmuş"

        if self.max_kullanim > 0 and self.kullanilan >= self.max_kullanim:
            return False, "İndirim kullanım limiti dolmuş"

        if harcama_tutari < self.min_harcama:
            return False, f"Minimum {self.min_harcama} TL harcama gerekli"

        return True, "Kullanılabilir"

    def indirim_uygula(self, adisyon):
        kontrol, mesaj = self.kullanilabilir_mi(adisyon.ara_toplam())

        if not kontrol:
            return False, mesaj

        if self.tip == 'yuzde':
            indirim = adisyon.ara_toplam() * self.deger / 100
        else:
            indirim = self.deger

        adisyon.indirim_tutari += indirim
        adisyon.save()

        self.kullanilan += 1
        self.save()

        return True, f"{indirim:.2f} TL indirim uygulandı"


# ==================== YENİ HIZLI SATIŞ MODELLERİ ====================

class HizliSatisCihaz(models.Model):
    """Hızlı satış için kullanılan POS cihazı ve yazıcı tanımları"""
    CIHAZ_TIPI = [
        ('pos', 'POS Cihazı'),
        ('yazici', 'Yazıcı'),
        ('kasa', 'Kasa'),
    ]
    BAGLANTI_TIPLERI = [
        ('ag', 'IP / Ag Yazicisi'),
        ('windows', 'Windows Yazicisi'),
    ]

    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='hizli_satis_cihazlari')
    cihaz_tipi = models.CharField(max_length=10, choices=CIHAZ_TIPI, verbose_name="Cihaz Tipi")
    ad = models.CharField(max_length=50, verbose_name="Cihaz Adı")
    baglanti_tipi = models.CharField(max_length=20, choices=BAGLANTI_TIPLERI, default='ag', verbose_name="Bağlantı Tipi")
    ip_adresi = models.GenericIPAddressField(verbose_name="IP Adresi", null=True, blank=True)
    port = models.IntegerField(default=9100, verbose_name="Port")
    windows_yazici_adi = models.CharField(max_length=255, blank=True, null=True, verbose_name="Windows Yazıcı Adı")
    seri_no = models.CharField(max_length=50, unique=True, verbose_name="Seri Numarası")
    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    kayit_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Hızlı Satış Cihazı"
        verbose_name_plural = "Hızlı Satış Cihazları"
        unique_together = ['sube', 'cihaz_tipi', 'seri_no']

    def __str__(self):
        return f"{self.sube.ad} - {self.get_cihaz_tipi_display()} - {self.ad}"

    def baglanti_hedefi(self):
        if self.baglanti_tipi == 'windows':
            return self.windows_yazici_adi or self.ad
        return f"{self.ip_adresi}:{self.port}"


class HizliSatisKasa(models.Model):
    """Her şube için ayrı hızlı satış kasası"""
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='hizli_satis_kasalari')
    kasa_no = models.CharField(max_length=20, verbose_name="Kasa Numarası")
    kasa_adi = models.CharField(max_length=50, verbose_name="Kasa Adı")

    pos_cihazi = models.ForeignKey(
        HizliSatisCihaz,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pos_kasalar',
        limit_choices_to={'cihaz_tipi': 'pos'}
    )
    yazici = models.ForeignKey(
        HizliSatisCihaz,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='yazici_kasalar',
        limit_choices_to={'cihaz_tipi': 'yazici'}
    )

    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    acilis_saati = models.TimeField(default="09:00", verbose_name="Açılış Saati")
    kapanis_saati = models.TimeField(default="23:00", verbose_name="Kapanış Saati")

    liste_sirasi = models.PositiveIntegerField(default=0, verbose_name="Listeleme sırası")
    favori_bir = models.BooleanField(
        default=False,
        verbose_name="Favori 1 (varsayılan kasa)",
        help_text="Şubede tek hesap varsayılan olur; kasa seçiminde ve raporlarda öncelik verilir.",
    )

    baslangic_bakiyesi = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Gün Başı Bakiyesi")
    gunluk_ciro = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Günlük Ciro")
    gunluk_satis_sayisi = models.IntegerField(default=0, verbose_name="Günlük Satış Sayısı")

    son_islem_tarihi = models.DateTimeField(null=True, blank=True, verbose_name="Son İşlem")
    son_islem_tutari = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Son İşlem Tutarı")

    class Meta:
        verbose_name = "Hızlı Satış Kasası"
        verbose_name_plural = "Hızlı Satış Kasaları"
        unique_together = [('sube', 'kasa_no')]
        ordering = ['liste_sirasi', 'kasa_no']

    def __str__(self):
        return f"{self.sube.ad} - {self.kasa_adi} ({self.kasa_no})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.favori_bir and self.sube_id:
            HizliSatisKasa.objects.filter(sube_id=self.sube_id).exclude(pk=self.pk).update(favori_bir=False)

    def gun_basi(self, bakiye):
        self.baslangic_bakiyesi = bakiye
        self.gunluk_ciro = 0
        self.gunluk_satis_sayisi = 0
        self.save()

        HizliSatisKasaHareket.objects.create(
            kasa=self,
            hareket_tipi='gun_basi',
            tutar=bakiye,
            aciklama=f"Gün başı bakiyesi: {bakiye} TL"
        )

    def gun_sonu(self):
        from datetime import date
        bugun = date.today()

        satislar = HizliSatis.objects.filter(
            kasa=self,
            tarih__date=bugun
        )

        toplam_satis = satislar.count()
        toplam_ciro = sum(s.toplam_tutar for s in satislar)
        nakit_toplam = sum(s.nakit_odenen for s in satislar)
        kart_toplam = sum(s.kart_odenen for s in satislar)

        HizliSatisKasaHareket.objects.create(
            kasa=self,
            hareket_tipi='gun_sonu',
            tutar=toplam_ciro,
            aciklama=f"Gün sonu - Satış: {toplam_satis}, Ciro: {toplam_ciro} TL"
        )

        return {
            'toplam_satis': toplam_satis,
            'toplam_ciro': toplam_ciro,
            'nakit_toplam': nakit_toplam,
            'kart_toplam': kart_toplam,
            'ortalama_satis': toplam_ciro / toplam_satis if toplam_satis > 0 else 0
        }


class HizliSatisKasaHareket(models.Model):
    """Kasa hareketleri (gün başı, gün sonu, devir vb.)"""
    HAREKET_TIPI = [
        ('gun_basi', 'Gün Başı'),
        ('gun_sonu', 'Gün Sonu'),
        ('devir', 'Devir'),
        ('sayim', 'Sayım'),
    ]

    kasa = models.ForeignKey(HizliSatisKasa, on_delete=models.CASCADE, related_name='kasa_hareketleri')
    hareket_tipi = models.CharField(max_length=10, choices=HAREKET_TIPI, verbose_name="Hareket Tipi")
    tutar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Tutar")
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İşlemi Yapan")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="İşlem Tarihi")

    class Meta:
        verbose_name = "Kasa Hareketi"
        verbose_name_plural = "Kasa Hareketleri"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.kasa} - {self.get_hareket_tipi_display()} - {self.tutar} TL"


class HizliSatisUrun(models.Model):
    """Hızlı satışa özel ürünler (barkodlu ürünler)"""
    BARKOD_TIPI = [
        ('EAN13', 'EAN-13'),
        ('EAN8', 'EAN-8'),
        ('CODE128', 'CODE128'),
        ('QR', 'QR Kod'),
    ]

    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='hizli_satis_urunleri')
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE, related_name='hizli_satis_urunleri')

    barkod = models.CharField(max_length=50, unique=True, verbose_name="Barkod")
    barkod_tipi = models.CharField(max_length=10, choices=BARKOD_TIPI, default='EAN13', verbose_name="Barkod Tipi")
    karekod_icerik = models.TextField(blank=True, null=True, verbose_name="Karekod İçeriği")

    satis_fiyati = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Satış Fiyatı")
    indirimli_fiyat = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, verbose_name="İndirimli Fiyat")
    stok_miktari = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Stok Miktarı")
    kritik_stok = models.DecimalField(max_digits=10, decimal_places=3, default=5, verbose_name="Kritik Stok Seviyesi")

    urun_gorseli = models.ImageField(upload_to='hizli_satis_urunleri/', blank=True, null=True, verbose_name="Ürün Görseli")

    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    indirimde_mi = models.BooleanField(default=False, verbose_name="İndirimde mi?")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Barkodlu Ürün"
        verbose_name_plural = "Barkodlu Ürünler"
        ordering = ['urun__ad']

    def __str__(self):
        return f"{self.sube.ad} - {self.urun.ad} ({self.barkod})"

    def gecerli_fiyat(self):
        return self.indirimli_fiyat if self.indirimde_mi and self.indirimli_fiyat else self.satis_fiyati

    def stok_durumu(self):
        if self.stok_miktari <= 0:
            return "Tükendi"
        elif self.stok_miktari <= self.kritik_stok:
            return "Kritik"
        return "Normal"


class HizliSatisSepet(models.Model):
    """Anlık satış sepeti"""
    kasa = models.ForeignKey(HizliSatisKasa, on_delete=models.CASCADE, related_name='sepetler')
    kullanici = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="İşlemi Yapan")
    musteri = models.ForeignKey(Musteri, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="Müşteri")

    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    baslangic_zamani = models.DateTimeField(auto_now_add=True, verbose_name="Başlangıç")
    guncelleme_zamani = models.DateTimeField(auto_now=True, verbose_name="Güncelleme")

    ara_toplam = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Ara Toplam")
    indirim_tutari = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="İndirim")
    kdv_tutari = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="KDV")
    genel_toplam = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Genel Toplam")

    class Meta:
        verbose_name = "Hızlı Satış Sepeti"
        verbose_name_plural = "Hızlı Satış Sepetleri"

    def __str__(self):
        return f"Sepet #{self.id} - {self.kasa} - {self.baslangic_zamani.strftime('%H:%M:%S')}"

    def sepet_guncelle(self):
        """Sepet toplamlarını güncelle"""
        items = self.sepet_items.filter(aktif=True)

        self.ara_toplam = sum((item.toplam_fiyat for item in items), Decimal('0.00'))
        self.kdv_tutari = sum((item.kdv_tutari for item in items), Decimal('0.00'))
        self.genel_toplam = self.ara_toplam - self.indirim_tutari

        if self.genel_toplam < Decimal('0.00'):
            self.genel_toplam = Decimal('0.00')

        self.ara_toplam = self.ara_toplam.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.kdv_tutari = self.kdv_tutari.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        self.genel_toplam = self.genel_toplam.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.save(update_fields=['ara_toplam', 'kdv_tutari', 'genel_toplam', 'guncelleme_zamani'])


class HizliSatisSepetItem(models.Model):
    """Sepetteki ürünler"""
    sepet = models.ForeignKey(HizliSatisSepet, on_delete=models.CASCADE, related_name='sepet_items')
    urun = models.ForeignKey(HizliSatisUrun, on_delete=models.CASCADE, verbose_name="Ürün")

    adet = models.DecimalField(max_digits=10, decimal_places=3, default=1, verbose_name="Adet/Miktar")
    birim_fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Birim Fiyat")
    toplam_fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Toplam Fiyat")

    indirim_yuzde = models.DecimalField(max_digits=5, decimal_places=2, default=0, verbose_name="İndirim %")
    indirim_tutari = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="İndirim Tutarı")

    kdv_orani = models.IntegerField(choices=Urun.KDV_CHOICES, default=10, verbose_name="KDV %")
    kdv_tutari = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="KDV Tutarı")

    aktif = models.BooleanField(default=True, verbose_name="Aktif")
    eklenme_zamani = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Sepet Ürünü"
        verbose_name_plural = "Sepet Ürünleri"

    def __str__(self):
        return f"{self.urun.urun.ad} x{self.adet}"

    def save(self, *args, **kwargs):
        # Ürün fiyatı zaten satış fiyatı / KDV dahil kabul edilir
        self.birim_fiyat = Decimal(str(self.urun.gecerli_fiyat())).quantize(
            Decimal('0.01'),
            rounding=ROUND_HALF_UP
        )

        adet_decimal = Decimal(str(self.adet))
        indirim_yuzde_decimal = Decimal(str(self.indirim_yuzde)) / Decimal('100')

        indirimli_birim_fiyat = (
            self.birim_fiyat * (Decimal('1.00') - indirim_yuzde_decimal)
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        self.indirim_tutari = (
            (self.birim_fiyat - indirimli_birim_fiyat) * adet_decimal
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # KDV bir daha eklenmez
        self.toplam_fiyat = (
            indirimli_birim_fiyat * adet_decimal
        ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

        # KDV sadece bilgi amaçlı, dahil fiyattan geri çıkarılır
        kdv_orani_decimal = Decimal(str(self.kdv_orani)) / Decimal('100')
        if kdv_orani_decimal > 0:
            self.kdv_tutari = (
                self.toplam_fiyat * kdv_orani_decimal / (Decimal('1.00') + kdv_orani_decimal)
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        else:
            self.kdv_tutari = Decimal('0.00')

        super().save(*args, **kwargs)

        self.sepet.sepet_guncelle()


class HizliSatis(models.Model):
    """Hızlı satış (take away / götür) modeli"""
    ODEME_TIPLERI = [
        ('nakit', 'Nakit'),
        ('kart', 'Kart'),
        ('karma', 'Karma'),
    ]

    kasa = models.ForeignKey(HizliSatisKasa, on_delete=models.CASCADE, related_name='hizli_satislar')
    sube = models.ForeignKey(Sube, on_delete=models.CASCADE, related_name='hizli_satislar')
    musteri = models.ForeignKey(Musteri, on_delete=models.SET_NULL, null=True, blank=True)

    fis_no = models.CharField(max_length=50, unique=True, verbose_name="Fiş No")
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Satış Tarihi")
    toplam_tutar = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Toplam Tutar")

    odeme_tipi = models.CharField(max_length=10, choices=ODEME_TIPLERI, default='nakit', verbose_name="Ödeme Tipi")
    nakit_odenen = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Nakit Ödenen")
    kart_odenen = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Kart Ödenen")
    para_ustu = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name="Para Üstü")

    kullanici = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name="İşlemi Yapan")
    notlar = models.TextField(blank=True, null=True, verbose_name="Notlar")

    class Meta:
        verbose_name = "Satış Ürün Kalemi"
        verbose_name_plural = "Satış Ürün Kalemleri"
        ordering = ['-tarih']

    def __str__(self):
        return f"{self.fis_no} - {self.tarih.strftime('%d.%m.%Y %H:%M')} - {self.toplam_tutar} TL"


class HizliSatisItem(models.Model):
    """Hızlı satış ürün kalemleri"""
    hizli_satis = models.ForeignKey(HizliSatis, on_delete=models.CASCADE, related_name='items')
    urun = models.ForeignKey(Urun, on_delete=models.CASCADE, verbose_name="Ürün")
    adet = models.PositiveIntegerField(default=1, verbose_name="Adet")
    birim_fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Birim Fiyat")
    toplam_fiyat = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Toplam Fiyat")

    stok_dusuldu = models.BooleanField(default=False, verbose_name="Stok Düşüldü mü?")

    class Meta:
        verbose_name = "Hızlı Satış Ürünü"
        verbose_name_plural = "Hızlı Satış Ürünleri"

    def __str__(self):
        return f"{self.urun.ad} x{self.adet}"

    def save(self, *args, **kwargs):
        self.birim_fiyat = self.urun.fiyat
        self.toplam_fiyat = self.urun.fiyat * self.adet
        super().save(*args, **kwargs)

# models.py


class TedarikciFatura(models.Model):
    fatura_no = models.CharField(max_length=100, unique=True)
    fatura_tarihi = models.DateField(null=True, blank=True)
    tedarikci_adi = models.CharField(max_length=255, blank=True)
    xml_dosyasi = models.FileField(upload_to="xml_faturalar/")
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.fatura_no


class StokHareketi(models.Model):
    HAREKET_TIPI = (
        ("giris", "Giriş"),
        ("cikis", "Çıkış"),
    )

    urun = models.ForeignKey("Urun", on_delete=models.CASCADE, related_name="stok_hareketleri")
    hareket_tipi = models.CharField(max_length=10, choices=HAREKET_TIPI)
    miktar = models.DecimalField(max_digits=12, decimal_places=3)
    birim_fiyat = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    aciklama = models.TextField(blank=True)
    fatura = models.ForeignKey(TedarikciFatura, null=True, blank=True, on_delete=models.SET_NULL)
    tarih = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.urun} - {self.hareket_tipi} - {self.miktar}"
    
class XMLUrunEsleme(models.Model):
    xml_urun_adi = models.CharField(max_length=255, db_index=True)
    xml_barkod = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    stok_kalemi = models.ForeignKey('StokKalemi', on_delete=models.CASCADE, related_name='xml_eslesmeleri')
    olusturma_tarihi = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "XML Ürün Eşleşmesi"
        verbose_name_plural = "XML Ürün Eşleşmeleri"
        unique_together = ('xml_urun_adi', 'xml_barkod')

    def __str__(self):
        return f"{self.xml_urun_adi} -> {self.stok_kalemi.ad}"
    
class UretimFis(models.Model):
    sube = models.ForeignKey("Sube", on_delete=models.CASCADE, verbose_name="Şube")
    urun = models.ForeignKey("Urun", on_delete=models.CASCADE, verbose_name="Ürün")
    miktar = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Üretim Miktarı")
    
    aciklama = models.TextField(blank=True, null=True, verbose_name="Açıklama")
    
    tarih = models.DateTimeField(auto_now_add=True, verbose_name="Tarih")
    olusturan = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.urun.ad} - {self.miktar} adet"
   
