from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from adisyon_modulu.backup_manager import YedeklemeYoneticisi
from adisyon_modulu.backup_service import aktif_yedekleme_ayari


class Command(BaseCommand):
    help = "Yerel yedeklerden otomatik geri yukleme yapar"

    def add_arguments(self, parser):
        parser.add_argument("--dosya", type=str, help="Geri yuklenecek zip dosya yolu veya dosya adi")
        parser.add_argument("--en-son", action="store_true", help="En son yedegi geri yukle")

    def handle(self, *args, **options):
        ayar = aktif_yedekleme_ayari()
        yonetici = YedeklemeYoneticisi(ayar)
        yedekler = yonetici.mevcut_yedekleri_listele()

        if not yedekler:
            raise CommandError("Geri yuklenecek yedek bulunamadi.")

        hedef = None
        if options["dosya"]:
            girilen = Path(options["dosya"])
            if girilen.exists():
                hedef = girilen
            else:
                hedef = Path(ayar.yerel_klasor) / options["dosya"]
        elif options["en_son"]:
            hedef = Path(yedekler[0]["yol"])

        if hedef is None or not hedef.exists():
            raise CommandError("Geri yuklenecek dosya bulunamadi.")

        sonuc = yonetici.geri_yukle(hedef)
        if not sonuc["basarili"]:
            raise CommandError(sonuc.get("hata", "Geri yukleme basarisiz."))

        self.stdout.write(self.style.SUCCESS(f"Geri yukleme tamamlandi: {hedef.name}"))
