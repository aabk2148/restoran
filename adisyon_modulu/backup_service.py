import logging

from django.utils import timezone

from .backup_manager import YedeklemeYoneticisi
from .models import YedekKaydi, YedeklemeAyarlari

logger = logging.getLogger(__name__)


def aktif_yedekleme_ayari():
    ayar = YedeklemeAyarlari.objects.order_by("id").first()
    if ayar is None:
        ayar = YedeklemeAyarlari.objects.create(aktif=True, yedekleme_tipi="yerel")
    return ayar


def format_bytes(value):
    boyut = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if boyut < 1024:
            return f"{boyut:.1f} {unit}"
        boyut /= 1024
    return f"{boyut:.1f} TB"


def yedekleme_zamani_geldi_mi(ayar, simdi=None):
    simdi = simdi or timezone.localtime(timezone.now())
    hedef_saat = ayar.yedekleme_saati

    if simdi.hour != hedef_saat.hour:
        return False
    if abs(simdi.minute - hedef_saat.minute) > 5:
        return False
    if ayar.son_yedekleme is None:
        return True

    son = timezone.localtime(ayar.son_yedekleme)
    gun_farki = (simdi.date() - son.date()).days
    return gun_farki >= ayar.zaman_araligi


def yedek_olustur_ve_kaydet(ayar, aciklama="Manuel yedek"):
    yedek_kaydi = YedekKaydi.objects.create(
        yedek_tipi=ayar.yedekleme_tipi,
        dosya_adi="hazirlaniyor.zip",
        durum="isleniyor",
        aciklama=aciklama,
    )

    yonetici = YedeklemeYoneticisi(ayar)
    sonuc = yonetici.yedek_olustur()

    if sonuc["basarili"]:
        yedek_kaydi.durum = "basari"
        yedek_kaydi.dosya_adi = sonuc["dosya_adi"]
        yedek_kaydi.dosya_boyutu = format_bytes(sonuc["boyut"])
        yedek_kaydi.hata_mesaji = ""
        yedek_kaydi.save(update_fields=["durum", "dosya_adi", "dosya_boyutu", "hata_mesaji"])

        ayar.son_yedekleme = timezone.now()
        ayar.save(update_fields=["son_yedekleme"])
    else:
        yedek_kaydi.durum = "basarisiz"
        yedek_kaydi.hata_mesaji = sonuc.get("hata", "Bilinmeyen hata")
        yedek_kaydi.save(update_fields=["durum", "hata_mesaji"])

    return sonuc


def otomatik_yedekleri_calistir():
    simdi = timezone.localtime(timezone.now())
    for ayar in YedeklemeAyarlari.objects.filter(aktif=True).order_by("id"):
        if not yedekleme_zamani_geldi_mi(ayar, simdi=simdi):
            continue
        try:
            yedek_olustur_ve_kaydet(ayar, aciklama="Otomatik zamanlanmis yedek")
        except Exception:
            logger.exception("Otomatik yedekleme calisirken hata olustu.")
