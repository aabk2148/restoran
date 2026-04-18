from django.core.management.base import BaseCommand
from adisyon_modulu.views import rezervasyon_otomatik_kontrol

class Command(BaseCommand):
    help = 'Süresi geçen rezervasyonları temizler ve hatırlatma gönderir'

    def handle(self, *args, **options):
        from django.test import RequestFactory
        factory = RequestFactory()
        request = factory.get('/')
        response = rezervasyon_otomatik_kontrol(request)
        self.stdout.write(self.style.SUCCESS('Rezervasyon kontrolü tamamlandı'))