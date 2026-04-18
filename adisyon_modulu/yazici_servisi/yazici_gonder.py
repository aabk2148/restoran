import socket
import requests
import time

def turkce_duzelt(metin):
    """Türkçe karakterleri ASCII karşılıklarına çevir"""
    donusum = {
        'ı': 'i', 'İ': 'I',
        'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U',
        'ş': 's', 'Ş': 'S',
        'ö': 'o', 'Ö': 'O',
        'ç': 'c', 'Ç': 'C',
    }
    for turkce, ascii_ in donusum.items():
        metin = metin.replace(turkce, ascii_)
    return metin

def yaziciya_gonder(ip, port, siparisler):
    """TÜM siparişleri TEK fişte yazdır"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        sock.connect((ip, port))
        print(f"✅ Yazıcıya bağlanıldı: {ip}:{port}")
        
        # ESC/POS komutları
        ESC = b'\x1b'
        GS = b'\x1d'
        
        # TEK bir fiş oluştur
        komutlar = bytearray()
        
        # Yazıcıyı sıfırla
        komutlar.extend(ESC + b'\x40')
        
        # Başlık - Ortalanmış büyük yazı
        komutlar.extend(ESC + b'\x61' + b'\x01')
        komutlar.extend(ESC + b'\x21' + b'\x30')
        komutlar.extend("ELAKI".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(ESC + b'\x21' + b'\x00')
        komutlar.extend("MUTFAK SIPARISLERI".encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(f"Saat: {time.strftime('%H:%M')}".encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        
        # Sola hizala
        komutlar.extend(ESC + b'\x61' + b'\x00')
        
        # Üst çizgi
        komutlar.extend(("=" * 32).encode('utf-8'))
        komutlar.extend(b'\x0a')
        
        # Tüm siparişleri tek tek ekle
        for i, item in enumerate(siparisler, 1):
            # Sipariş numarası
            komutlar.extend(ESC + b'\x45' + b'\x01')  # Kalın aç
            komutlar.extend(f"SIPARIS #{i}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x45' + b'\x00')  # Kalın kapa
            
            # Masa
            komutlar.extend(f"MASA: {item['masa']}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            
            # Ürün (Türkçe karakter düzeltildi)
            urun_adi = turkce_duzelt(item['urun'])
            komutlar.extend(f"URUN: {urun_adi}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            
            # Adet (büyük yazı)
            komutlar.extend(ESC + b'\x21' + b'\x11')  # Çift yükseklik
            komutlar.extend(f"ADET: {item['adet']}".encode('utf-8'))
            komutlar.extend(b'\x0a')
            komutlar.extend(ESC + b'\x21' + b'\x00')  # Normal yazı
            
            # Not (varsa)
            if item.get('not') and item['not']:
                komutlar.extend(f"NOT: {item['not']}".encode('utf-8'))
                komutlar.extend(b'\x0a')
            
            # Siparişler arası çizgi (son sipariş değilse)
            if i < len(siparisler):
                komutlar.extend(("-" * 32).encode('utf-8'))
                komutlar.extend(b'\x0a')
        
        # Alt çizgi ve toplam
        komutlar.extend(("=" * 32).encode('utf-8'))
        komutlar.extend(b'\x0a')
        komutlar.extend(ESC + b'\x21' + b'\x11')  # Çift yükseklik
        komutlar.extend(f"TOPLAM: {len(siparisler)} SIPARIS".encode('utf-8'))
        komutlar.extend(b'\x0a\x0a')
        komutlar.extend(ESC + b'\x21' + b'\x00')
        
        # Kağıt kes
        komutlar.extend(GS + b'\x56' + b'\x41' + b'\x00')
        
        # TEK seferde yazıcıya gönder
        sock.send(komutlar)
        print(f"📨 TOPLU FİŞ yazdırıldı: {len(siparisler)} sipariş")
        
        sock.close()
        return True
        
    except Exception as e:
        print(f"❌ Yazıcı hatası: {e}")
        return False

def main():
    print("\n" + "="*50)
    print("🖨️  YAZICI SERVISI BASLATILDI (TOPLU FIS)")
    print("="*50)
    
    YAZICI_IP = "192.168.1.222"
    YAZICI_PORT = 9100
    API_URL = "http://127.0.0.1:8000/api/yazici/1/"
    
    while True:
        try:
            response = requests.get(API_URL, timeout=3)
            
            if response.status_code == 200:
                siparisler = response.json()
                
                if siparisler:
                    print(f"\n📦 {len(siparisler)} yeni siparis bulundu")
                    yaziciya_gonder(YAZICI_IP, YAZICI_PORT, siparisler)
                else:
                    print(".", end="", flush=True)
            
            time.sleep(3)
            
        except requests.exceptions.ConnectionError:
            print("\n⚠️  Django sunucusuna baglanilamiyor")
            time.sleep(5)
        except KeyboardInterrupt:
            print("\n\n🛑 Servis durduruldu")
            break
        except Exception as e:
            print(f"\n❌ Hata: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()