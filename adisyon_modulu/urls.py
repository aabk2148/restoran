from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from .views import (
    auth_views,
    masa_views,
    paket_views,
    mutfak_views,
    rezervasyon_views,
    rapor_views,
    stok_views,
    api_views,
    yedekleme_views,
    yazici_views,
    musteri_views,
    hizli_satis_views,
    puantaj_views,
    menu_views,
)

from adisyon_modulu.views import urun_views
from adisyon_modulu.views.urun_views import (
    urun_listesi,
    urun_ekle,
    urun_duzenle,
    urun_sil,
    kategori_listesi,
    kategori_ekle,
    kategori_duzenle,
    kategori_sil,
)
from adisyon_modulu.views.stok_views import xml_fatura_yukle, xml_eslesme_kaydet
from .views.uretim_views import uretim_ekrani, uretim_kaydet
from .views.yonetim_views import yonetim_paneli
from .module_control import module_required

urlpatterns = [
    # --- Ana Giriş ve Yönlendirme ---
    path('', auth_views.ana_sayfa, name='ana_sayfa'),
    path('giris-yonlendir/', auth_views.giris_sonrasi_yonlendir, name='giris_sonrasi_yonlendir'),

    # --- Masa ve Şube ---
    path('sube/<int:sube_id>/', masa_views.sube_detay, name='sube_detay'),
    path('masa/<int:masa_id>/', masa_views.masa_detay, name='masa_detay'),

    # --- Sipariş İşlemleri ---
    path('masa/<int:masa_id>/ekle/', masa_views.siparis_ekle, name='siparis_ekle'),
    path('adisyon/<int:adisyon_id>/kapat/', masa_views.masa_kapat, name='masa_kapat'),
    path('adisyon/<int:adisyon_id>/tasi/', masa_views.masa_tasi_birlestir, name='masa_tasi_birlestir'),
    path('siparis-sil/<int:item_id>/', masa_views.siparis_sil, name='siparis_sil'),
    path('ikram-yap/<int:item_id>/', masa_views.ikram_yap, name='ikram_yap'),
    path('indirim-yap/<int:adisyon_id>/', masa_views.indirim_yap, name='indirim_yap'),
    path('siparis-adet-artir/<int:item_id>/', masa_views.siparis_adet_artir, name='siparis_adet_artir'),
    path('siparis-adet-azalt/<int:item_id>/', masa_views.siparis_adet_azalt, name='siparis_adet_azalt'),
    path('siparis-ozel-istek/<int:item_id>/', masa_views.siparis_ozel_istek, name='siparis_ozel_istek'),
    path('adisyon/<int:adisyon_id>/musteri-ekle/', masa_views.adisyon_musteri_ekle, name='adisyon_musteri_ekle'),

    # --- Paket Servis ---
    path('paket-servis/<int:sube_id>/', paket_views.paket_servis_ana, name='paket_servis_ana'),
    path('paket-servis/<int:sube_id>/ekle/', paket_views.musteri_ekle, name='musteri_ekle_paket'),
    path('paket-servis/<int:sube_id>/olustur/<int:musteri_id>/', paket_views.paket_siparis_olustur, name='paket_siparis_olustur'),
    path('paket-detay/<int:adisyon_id>/', paket_views.paket_detay, name='paket_detay'),
    path('paket-siparis-ekle/<int:adisyon_id>/', paket_views.paket_siparis_ekle, name='paket_siparis_ekle'),
    path('paket-durum/<int:adisyon_id>/', paket_views.paket_durum_degistir, name='paket_durum_degistir'),
    path('paket-fis-yazdir/<int:adisyon_id>/', paket_views.paket_fis_yazdir, name='paket_fis_yazdir'),

    # --- Mutfak Ekranları ---
    path('mutfak/', module_required('kitchen-panel')(mutfak_views.mutfak_ana_sayfa), name='mutfak_ana_sayfa'),
    path('mutfak/sube/<int:sube_id>/', module_required('kitchen-panel')(mutfak_views.mutfak_bolge_secimi), name='mutfak_bolge_secimi'),
    path('mutfak/bolge/<int:bolge_id>/', module_required('kitchen-panel')(mutfak_views.mutfak_ekrani_filtreli), name='mutfak_ekrani_filtreli'),
    path('mutfak/hazir/<int:item_id>/', module_required('kitchen-panel')(mutfak_views.siparis_hazir_isaretle), name='siparis_hazir_isaretle'),
    path('adisyon/<int:adisyon_id>/yazdir-mutfak/', mutfak_views.toplu_mutfak_yazdir, name='toplu_mutfak_yazdir'),

    # --- Raporlar ve Gider ---
    path('raporlar/', module_required('reports-panel')(rapor_views.rapor_sayfasi), name='rapor_sayfasi'),
    path('raporlar/<int:sube_id>/', module_required('reports-panel')(rapor_views.rapor_sayfasi), name='rapor_sayfasi_sube'),
    path('gider-ekle/', module_required('expense-entry')(rapor_views.gider_ekle), name='gider_ekle'),

    # --- QR Menü ve API ---
    path('menu/<int:sube_id>/', api_views.qr_menu, name='qr_menu'),
    path('api/menu-siparis/<int:sube_id>/', menu_views.menu_siparis_talebi_olustur, name='menu_siparis_talebi_olustur'),
    path('api/garson-cagir/<int:sube_id>/', masa_views.api_garson_cagir, name='api_garson_cagir'),
    path('api/yazici/<int:sube_id>/', api_views.yerel_yazici_api, name='yazici_api'),
    path('api/bildirim/<int:sube_id>/', api_views.bildirim_kontrol, name='bildirim_kontrol'),
    path('api/masa-uygunluk/', api_views.masa_uygunluk_kontrol, name='masa_uygunluk_kontrol'),
    path('api/masa-kilit-kontrol/', api_views.masa_kilit_kontrol_api, name='masa_kilit_kontrol'),
    path('api/masa-plani-kaydet/', masa_views.api_masa_plani_kaydet, name='api_masa_plani_kaydet'),
    path('api/urun-sira-kaydet/', api_views.api_urun_sira_kaydet, name='api_urun_sira_kaydet'),

    # --- Rezervasyon ---
    path('rezervasyonlar/', module_required('reservation-list')(rezervasyon_views.rezervasyon_listesi), name='rezervasyon_listesi'),
    path('rezervasyon-ekle/', module_required('reservation-new')(rezervasyon_views.rezervasyon_ekle), name='rezervasyon_ekle'),
    path('rezervasyon-ekle/<int:sube_id>/', module_required('reservation-new')(rezervasyon_views.rezervasyon_ekle), name='rezervasyon_ekle_sube'),
    path('rezervasyon-detay/<int:rezervasyon_id>/', module_required('reservation-list')(rezervasyon_views.rezervasyon_detay), name='rezervasyon_detay'),
    path('rezervasyon-onay/<int:rezervasyon_id>/', module_required('reservation-list')(rezervasyon_views.rezervasyon_onay), name='rezervasyon_onay'),
    path('rezervasyon-iptal/<int:rezervasyon_id>/', module_required('reservation-list')(rezervasyon_views.rezervasyon_iptal), name='rezervasyon_iptal'),
    path('rezervasyon-gelmedi/<int:rezervasyon_id>/', module_required('reservation-list')(rezervasyon_views.rezervasyon_gelmedi), name='rezervasyon_gelmedi'),
    path('rezervasyon-tamamla/<int:rezervasyon_id>/', module_required('reservation-list')(rezervasyon_views.rezervasyon_tamamla), name='rezervasyon_tamamla'),
    path('rezervasyon-masa-ata/<int:rezervasyon_id>/', module_required('reservation-list')(rezervasyon_views.rezervasyon_masa_ata), name='rezervasyon_masa_ata'),
    path('api/rezervasyon-otomatik-kontrol/', module_required('reservation-list')(rezervasyon_views.rezervasyon_otomatik_kontrol), name='rezervasyon_otomatik_kontrol'),

    # --- Tedarikçi ve Stok ---
    path('tedarikciler/', module_required('suppliers')(stok_views.tedarikci_listesi), name='tedarikci_listesi'),
    path('tedarikci-ekle/', module_required('suppliers')(stok_views.tedarikci_ekle), name='tedarikci_ekle'),
    path('tedarikci-duzenle/<int:tedarikci_id>/', module_required('suppliers')(stok_views.tedarikci_duzenle), name='tedarikci_duzenle'),
    path('tedarikci-sil/<int:tedarikci_id>/', module_required('suppliers')(stok_views.tedarikci_sil), name='tedarikci_sil'),
    path('stok-giris/<int:stok_id>/', module_required('suppliers')(stok_views.stok_giris), name='stok_giris'),

    # --- Yedekleme ---
    path('yedekleme/', module_required('backup')(yedekleme_views.yedekleme_sayfasi), name='yedekleme_sayfasi'),
    path('yedekleme/ayarlar/', module_required('backup')(yedekleme_views.yedekleme_ayarlari_kaydet), name='yedekleme_ayarlari_kaydet'),
    path('yedek-al/', module_required('backup')(yedekleme_views.yedek_al_manuel), name='yedek_al_manuel'),
    path('yedek-geri-yukle/', module_required('backup')(yedekleme_views.yedek_geri_yukle), name='yedek_geri_yukle'),
    path('yazici-yonetimi/', module_required('printer-management')(yazici_views.yazici_yonetimi), name='yazici_yonetimi'),

    # --- Müşteri İşlemleri ---
    path('musteri-ara/', module_required('loyalty')(musteri_views.musteri_ara), name='musteri_ara'),
    path('musteri-ekle/', module_required('loyalty')(musteri_views.musteri_ekle), name='musteri_ekle'),
    path('musteri-profil/<int:musteri_id>/', module_required('loyalty')(musteri_views.musteri_profil), name='musteri_profil'),
    path('kupon-kullan/<int:kupon_id>/<int:adisyon_id>/', module_required('loyalty')(musteri_views.kupon_kullan), name='kupon_kullan'),
    path('kisisel-indirim-uygula/<int:indirim_id>/<int:adisyon_id>/', module_required('loyalty')(musteri_views.kisisel_indirim_uygula), name='kisisel_indirim_uygula'),
    path('api/musteri-puan/<int:musteri_id>/', module_required('loyalty')(musteri_views.musteri_puan_goruntule), name='musteri_puan_api'),

    # --- Hızlı Satış ---
    path('hizli-satis/kasa-secim/', module_required('quick-sale')(hizli_satis_views.kasa_secim), name='kasa_secim'),
    path('hizli-satis/api/kasa-sira-kaydet/', module_required('quick-sale')(hizli_satis_views.kasa_liste_sira_kaydet), name='kasa_liste_sira_kaydet'),
    path('hizli-satis/api/kasa-favori-kaydet/', module_required('quick-sale')(hizli_satis_views.kasa_favori_bir_kaydet), name='kasa_favori_bir_kaydet'),
    path('hizli-satis/kasa/<int:kasa_id>/', module_required('quick-sale')(hizli_satis_views.kasa_ekrani), name='kasa_ekrani'),
    path('hizli-satis/api/barkod-oku/', module_required('quick-sale')(hizli_satis_views.barkod_oku), name='barkod_oku'),
    path('hizli-satis/api/sepet/<int:sepet_id>/guncelle/', module_required('quick-sale')(hizli_satis_views.sepet_guncelle), name='sepet_guncelle'),
    path('hizli-satis/sepet/<int:sepet_id>/temizle/', module_required('quick-sale')(hizli_satis_views.sepet_temizle), name='sepet_temizle'),
    path('hizli-satis/sepet/<int:sepet_id>/odeme/', module_required('quick-sale')(hizli_satis_views.odeme_ekrani), name='odeme_ekrani'),
    path('hizli-satis/api/sepet/<int:sepet_id>/odeme-tamamla/', module_required('quick-sale')(hizli_satis_views.odeme_tamamla), name='odeme_tamamla'),
    path('hizli-satis/api/karekod/<int:urun_id>/', module_required('quick-sale')(hizli_satis_views.karekod_olustur), name='karekod_olustur'),
    path('hizli-satis/kasa/<int:kasa_id>/gun-sonu/', module_required('quick-sale')(hizli_satis_views.gun_sonu), name='gun_sonu'),
    path('hizli-satis/kasa/<int:kasa_id>/satis-gecmisi/', module_required('quick-sale')(hizli_satis_views.satis_gecmisi), name='satis_gecmisi'),
    path('hizli-satis/api/musteri-ara/', module_required('quick-sale')(hizli_satis_views.api_musteri_ara), name='api_musteri_ara'),
    path('hizli-satis/api/satis-detay/<int:satis_id>/', module_required('quick-sale')(hizli_satis_views.api_satis_detay), name='api_satis_detay'),
    path('hizli-satis/export/<str:format_type>/', module_required('quick-sale')(hizli_satis_views.satis_export), name='satis_export'),
    path('hizli-satis/fis-yazdir/<int:satis_id>/', module_required('quick-sale')(hizli_satis_views.fis_yazdir_sayfa), name='fis_yazdir'),
    path('hizli-satis/kasa/<int:kasa_id>/export/<str:format_type>/', module_required('quick-sale')(hizli_satis_views.satis_export), name='satis_export_kasa'),

    # --- Lisans ---
    path('lisans-aktivasyon/', auth_views.lisans_aktivasyon_view, name='lisans_aktivasyon'),

    # --- Ürün Yönetimi ---
    path('urunler/', module_required('products')(urun_listesi), name='urun_listesi'),
    path('urunler/ekle/', module_required('products')(urun_ekle), name='urun_ekle'),
    path('urunler/<int:urun_id>/duzenle/', module_required('products')(urun_duzenle), name='urun_duzenle'),
    path('urunler/<int:urun_id>/sil/', module_required('products')(urun_sil), name='urun_sil'),

    # --- Kategori Yönetimi ---
    path('kategoriler/', module_required('products')(kategori_listesi), name='kategori_listesi'),
    path('kategoriler/ekle/', module_required('products')(kategori_ekle), name='kategori_ekle'),
    path('kategoriler/<int:kategori_id>/duzenle/', module_required('products')(kategori_duzenle), name='kategori_duzenle'),
    path('kategoriler/<int:kategori_id>/sil/', module_required('products')(kategori_sil), name='kategori_sil'),

    # --- Alerjen Yönetimi ---
    path('urunler/alerjenler/', module_required('products')(urun_views.alerjen_listesi), name='alerjen_listesi'),
    path('urunler/alerjenler/ekle/', module_required('products')(urun_views.alerjen_ekle), name='alerjen_ekle'),
    path('urunler/alerjenler/<int:pk>/duzenle/', module_required('products')(urun_views.alerjen_duzenle), name='alerjen_duzenle'),
    path('urunler/alerjenler/<int:pk>/sil/', module_required('products')(urun_views.alerjen_sil), name='alerjen_sil'),

    # --- Dil ---
    path('i18n/', include('django.conf.urls.i18n')),

    # --- XML ---
    path('xml-yukle/', module_required('xml-transfer')(xml_fatura_yukle), name='xml_yukle'),
    path('xml-eslesme-kaydet/', module_required('xml-transfer')(xml_eslesme_kaydet), name='xml_eslesme_kaydet'),

    # --- Üretim / Yönetim ---
    path('uretim/', module_required('production')(uretim_ekrani), name='uretim_ekrani'),
    path('uretim/kaydet/', module_required('production')(uretim_kaydet), name='uretim_kaydet'),
    path('yonetim-paneli/', module_required('management-home')(yonetim_paneli), name='yonetim_paneli'),

    # --- Garson Paneli ---
    path('garson-paneli/', module_required('waiter-panel')(masa_views.garson_paneli), name='garson_paneli'),
    path('garson-cagri/<int:cagri_id>/tamamla/', module_required('waiter-panel')(masa_views.garson_cagri_tamamla), name='garson_cagri_tamamla'),
    path('garson-cagrilar/temizle/', module_required('waiter-panel')(masa_views.garson_tamamlananlari_temizle), name='garson_tamamlananlari_temizle'),
    path('puantaj/', module_required('puantaj-panel')(puantaj_views.puantaj_paneli), name='puantaj_paneli'),
    path('puantaj/hareket/', module_required('puantaj-panel')(puantaj_views.puantaj_hareketi), name='puantaj_hareketi'),
    path('menu-siparis-onay/', menu_views.menu_siparis_onay_listesi, name='menu_siparis_onay_listesi'),
    path('menu-siparis-onay/<int:talep_id>/onayla/', menu_views.menu_siparis_onayla, name='menu_siparis_onayla'),
    path('menu-siparis-onay/<int:talep_id>/reddet/', menu_views.menu_siparis_reddet, name='menu_siparis_reddet'),

    # --- Masa Yönetimi ---
    path('masa-yonetim/', module_required('table-admin')(masa_views.masa_yonetim_listesi), name='masa_yonetim_listesi'),
    path('masa/<int:masa_id>/sil/', module_required('table-admin')(masa_views.masa_sil), name='masa_sil'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
