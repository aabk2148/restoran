from django.core.management.base import BaseCommand
from django.utils import timezone

from adisyon_modulu.backup_service import yedek_olustur_ve_kaydet, yedekleme_zamani_geldi_mi
from adisyon_modulu.models import YedeklemeAyarlari


class Command(BaseCommand):
    help = "Manuel veya otomatik yedek alir"

    def add_arguments(self, parser):
        parser.add_argument("--tip", type=str, help="Yedek tipi (yerel/google_drive/dropbox)")
        parser.add_argument("--otomatik", action="store_true", help="Zamanlanmis otomatik gorev olarak calistir")

    def handle(self, *args, **options):
        ayarlar = YedeklemeAyarlari.objects.filter(aktif=True).order_by("id")
        if options["tip"]:
            ayarlar = ayarlar.filter(yedekleme_tipi=options["tip"])

        simdi = timezone.localtime(timezone.now())
        for ayar in ayarlar:
            if options["otomatik"] and not yedekleme_zamani_geldi_mi(ayar, simdi=simdi):
                self.stdout.write(
                    f"[{ayar.yedekleme_tipi}] Saat veya periyot uygun degil "
                    f"(Hedef: {ayar.yedekleme_saati.strftime('%H:%M')}, Simdi: {simdi.strftime('%H:%M')})"
                )
                continue

            self.stdout.write(f"Yedek aliniyor: {ayar}")
            sonuc = yedek_olustur_ve_kaydet(
                ayar,
                aciklama="Otomatik zamanlanmis yedek" if options["otomatik"] else "Komut satirindan manuel yedek",
            )

            if sonuc["basarili"]:
                self.stdout.write(self.style.SUCCESS(f"Yedek basarili: {sonuc['dosya_adi']}"))
            else:
                self.stdout.write(self.style.ERROR(f"Yedek basarisiz: {sonuc.get('hata', 'Bilinmeyen hata')}"))
