from django.core.management.base import BaseCommand
from adisyon_modulu.stok_uyari import StokUyariServisi

class Command(BaseCommand):
    help = 'Kritik stokları kontrol eder ve uyarı gönderir'
    
    def handle(self, *args, **options):
        self.stdout.write("Stok kontrolü başlatılıyor...")
        
        uyarilar = StokUyariServisi.kontrol_et()
        
        if uyarilar:
            for uyari in uyarilar:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{uyari['sube'].ad}: {uyari['stoklar'].count()} kritik stok"
                    )
                )
        else:
            self.stdout.write(self.style.SUCCESS("Kritik stok bulunamadı."))