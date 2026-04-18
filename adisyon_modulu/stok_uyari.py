# stok_uyari.py
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from .models import StokKalemi, Sube
import logging

logger = logging.getLogger(__name__)

class StokUyariServisi:
    """Kritik stokları kontrol eden ve uyarı gönderen servis"""
    
    @staticmethod
    def kontrol_et():
        """Tüm şubelerdeki kritik stokları kontrol et"""
        uyarilar = []
        
        for sube in Sube.objects.all():
            # Kritik stoktaki ürünler (miktar <= kritik_seviye ve uyarı verilmemiş)
            kritik_stoklar = StokKalemi.objects.filter(
                sube=sube,
                miktar__lte=F('kritik_seviye'),
                uyari_verildi=False
            )
            
            if kritik_stoklar.exists():
                # Uyarı listesine ekle
                uyarilar.append({
                    'sube': sube,
                    'stoklar': kritik_stoklar
                })
                
                # Uyarı verildi olarak işaretle
                for stok in kritik_stoklar:
                    stok.uyari_verildi = True
                    stok.uyari_tarihi = timezone.now()
                    stok.save()
                
                # E-posta gönder
                StokUyariServisi.eposta_gonder(sube, kritik_stoklar)
                
                logger.info(f"{sube.ad} şubesinde {kritik_stoklar.count()} kritik stok tespit edildi.")
        
        return uyarilar
    
    @staticmethod
    def eposta_gonder(sube, kritik_stoklar):
        """Kritik stoklar için e-posta gönder"""
        konu = f"⚠️ KRİTİK STOK UYARISI - {sube.ad}"
        
        mesaj = f"""
        {sube.ad} şubesinde aşağıdaki ürünler kritik seviyenin altına düşmüştür:
        
        """
        
        for stok in kritik_stoklar:
            mesaj += f"""
            Ürün: {stok.ad}
            Mevcut Miktar: {stok.miktar} {stok.birim}
            Kritik Seviye: {stok.kritik_seviye} {stok.birim}
            Tedarikçi: {stok.tedarikci.ad if stok.tedarikci else 'Tanımlanmamış'}
            """
            if stok.tedarikci:
                mesaj += f"""
            Tedarikçi Tel: {stok.tedarikci.telefon}
            Tedarikçi Email: {stok.tedarikci.email}
            """
            mesaj += "\n" + "-"*50 + "\n"
        
        # Yöneticilere gönder
        from .models import KullaniciProfili
        yoneticiler = KullaniciProfili.objects.filter(
            rol__in=['Yonetici', 'Muhasebe'],
            aktif=True
        ).select_related('user')
        
        alicilar = [p.user.email for p in yoneticiler if p.user.email]
        
        if alicilar:
            try:
                send_mail(
                    konu,
                    mesaj,
                    settings.DEFAULT_FROM_EMAIL,
                    alicilar,
                    fail_silently=False,
                )
                logger.info(f"Kritik stok uyarısı {len(alicilar)} kişiye gönderildi.")
            except Exception as e:
                logger.error(f"E-posta gönderilemedi: {e}")
    
    @staticmethod
    def uyari_sifirla(stok_id):
        """Stok eklendikten sonra uyarı durumunu sıfırla"""
        try:
            stok = StokKalemi.objects.get(id=stok_id)
            stok.uyari_verildi = False
            stok.uyari_tarihi = None
            stok.save()
            return True
        except StokKalemi.DoesNotExist:
            return False