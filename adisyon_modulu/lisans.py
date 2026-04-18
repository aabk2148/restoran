import hashlib
import json
import os
import platform
import shutil
import ssl
import uuid
from datetime import datetime
from pathlib import Path

import requests

try:
    import certifi
except Exception:
    certifi = None


class LisansYoneticisi:
    """RestoranMaster lisans yonetim sinifi."""

    OFFLINE_GRACE_DAYS = 7

    def __init__(self):
        self.sunucu = "https://elaki.pythonanywhere.com"
        self.uygulama_klasoru = self._uygulama_veri_klasoru()
        self.uygulama_klasoru.mkdir(parents=True, exist_ok=True)

        self.eski_lisans_dosyasi = Path(os.path.dirname(os.path.dirname(__file__))) / "lisans_bilgisi.json"
        self.lisans_dosyasi = self.uygulama_klasoru / "lisans_bilgisi.json"
        self.cihaz_kimligi_dosyasi = self.uygulama_klasoru / "cihaz_kimligi.json"

    def _uygulama_veri_klasoru(self):
        appdata = os.environ.get("APPDATA")
        adaylar = []
        if appdata:
            adaylar.append(Path(appdata) / "Elaki")
        adaylar.append(Path.home() / "AppData" / "Roaming" / "Elaki")
        adaylar.append(Path(os.path.dirname(os.path.dirname(__file__))))

        for aday in adaylar:
            try:
                aday.mkdir(parents=True, exist_ok=True)
                return aday
            except Exception:
                continue

        return Path(os.path.dirname(os.path.dirname(__file__)))

    def _json_oku(self, dosya_yolu):
        try:
            if Path(dosya_yolu).exists():
                with open(dosya_yolu, "r", encoding="utf-8") as handle:
                    return json.load(handle)
        except Exception as exc:
            print(f"JSON okunamadi ({dosya_yolu}): {exc}")
        return None

    def _json_yaz(self, dosya_yolu, veri):
        Path(dosya_yolu).parent.mkdir(parents=True, exist_ok=True)
        with open(dosya_yolu, "w", encoding="utf-8") as handle:
            json.dump(veri, handle, indent=2, ensure_ascii=False)

    def _verify_bundle(self):
        adaylar = []

        try:
            if certifi:
                bundle = certifi.where()
                if bundle:
                    adaylar.append(bundle)
        except Exception:
            pass

        for env_adi in ("REQUESTS_CA_BUNDLE", "SSL_CERT_FILE"):
            env_degeri = os.environ.get(env_adi)
            if env_degeri:
                adaylar.append(env_degeri)

        try:
            varsayilan = ssl.get_default_verify_paths()
            for yol in (
                varsayilan.cafile,
                varsayilan.openssl_cafile,
            ):
                if yol:
                    adaylar.append(yol)
        except Exception:
            pass

        for aday in adaylar:
            try:
                if aday and Path(aday).exists():
                    return str(aday)
            except Exception:
                continue

        return True

    def _eski_lisansi_tasi(self):
        if self.lisans_dosyasi.exists() or not self.eski_lisans_dosyasi.exists():
            return
        try:
            shutil.copy2(self.eski_lisans_dosyasi, self.lisans_dosyasi)
        except Exception as exc:
            print(f"Eski lisans dosyasi tasinamadi: {exc}")

    def _legacy_makine_kodu_uret(self):
        try:
            bilgisayar_adi = platform.node()
            islemci = platform.processor()
            mac = hex(uuid.getnode())

            disk_kodu = "BILINMIYOR"
            try:
                import wmi

                diskler = wmi.WMI().Win32_DiskDrive()
                if diskler:
                    disk_kodu = (diskler[0].SerialNumber or "").strip() or "BILINMIYOR"
            except Exception:
                pass

            ham_kod = f"{bilgisayar_adi}-{islemci}-{mac}-{disk_kodu}"
            return hashlib.md5(ham_kod.encode()).hexdigest()
        except Exception as exc:
            print(f"Legacy makine kodu uretilemedi: {exc}")
            return None

    def _cihaz_kimligi_yukle(self):
        veri = self._json_oku(self.cihaz_kimligi_dosyasi)
        if veri and veri.get("makine_kodu"):
            return veri["makine_kodu"]
        return None

    def _cihaz_kimligi_kaydet(self, makine_kodu, kaynak="sabit"):
        try:
            self._json_yaz(
                self.cihaz_kimligi_dosyasi,
                {
                    "makine_kodu": makine_kodu,
                    "kaynak": kaynak,
                    "olusturma_tarihi": datetime.now().isoformat(),
                },
            )
            return True
        except Exception as exc:
            print(f"Cihaz kimligi kaydedilemedi: {exc}")
            return False

    def makine_kodu_uret(self):
        """Bu bilgisayara ozel ama sabit makine kodu uret."""
        try:
            sabit_kod = self._cihaz_kimligi_yukle()
            if sabit_kod:
                return sabit_kod

            self._eski_lisansi_tasi()
            kayitli_lisans = self._json_oku(self.lisans_dosyasi) or self._json_oku(self.eski_lisans_dosyasi)
            if kayitli_lisans and kayitli_lisans.get("makine_kodu"):
                makine_kodu = kayitli_lisans["makine_kodu"]
                self._cihaz_kimligi_kaydet(makine_kodu, kaynak="mevcut_lisans")
                return makine_kodu

            legacy_kod = self._legacy_makine_kodu_uret()
            if legacy_kod:
                self._cihaz_kimligi_kaydet(legacy_kod, kaynak="legacy")
                return legacy_kod

            rastgele_kod = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()
            self._cihaz_kimligi_kaydet(rastgele_kod, kaynak="uuid")
            return rastgele_kod
        except Exception as exc:
            print(f"Makine kodu uretilemedi: {exc}")
            return hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

    def lisans_kaydet(self, lisans_kodu, makine_kodu, sonuc):
        """Aktivasyon bilgilerini dosyaya kaydet."""
        try:
            veri = {
                "lisans_kodu": lisans_kodu,
                "makine_kodu": makine_kodu,
                "kayit_tarihi": datetime.now().isoformat(),
                "bitis_tarihi": sonuc.get("lisans_bilgileri", {}).get("bitis_tarihi"),
                "musteri": sonuc.get("lisans_bilgileri", {}).get("musteri"),
                "son_kontrol": datetime.now().isoformat(),
            }
            self._json_yaz(self.lisans_dosyasi, veri)
            self._cihaz_kimligi_kaydet(makine_kodu, kaynak="aktivasyon")
            return True
        except Exception as exc:
            print(f"Lisans kaydedilemedi: {exc}")
            return False

    def lisans_yukle(self):
        """Kayitli lisans bilgilerini oku."""
        self._eski_lisansi_tasi()
        veri = self._json_oku(self.lisans_dosyasi)
        if veri:
            return veri
        return self._json_oku(self.eski_lisans_dosyasi)

    def aktivasyon_yap(self, lisans_kodu):
        """Ilk calistirmada lisansi aktiflestir."""
        try:
            makine_kodu = self.makine_kodu_uret()

            response = requests.post(
                f"{self.sunucu}/aktivasyon",
                json={
                    "lisans_kodu": lisans_kodu.strip().upper(),
                    "makine_kodu": makine_kodu,
                },
                timeout=10,
                verify=self._verify_bundle(),
            )

            if response.status_code == 200:
                sonuc = response.json()
                if sonuc.get("durum") == "başarılı":
                    self.lisans_kaydet(lisans_kodu, makine_kodu, sonuc)
                    return True, sonuc
                return False, sonuc.get("mesaj", "Bilinmeyen hata")

            return False, f"Sunucu hatası: {response.status_code}"
        except requests.exceptions.ConnectionError:
            return False, "Lisans sunucusuna bağlanılamadı. İnternet bağlantınızı kontrol edin."
        except Exception as exc:
            return False, f"Hata: {str(exc)}"

    def lisans_kontrol(self):
        """Her sayfa yuklemesinde lisansi kontrol et."""
        try:
            kayit = self.lisans_yukle()
            if not kayit:
                return False, "Lisans aktif edilmemiş", None

            lisans_kodu = kayit.get("lisans_kodu")
            kayitli_makine_kodu = kayit.get("makine_kodu")
            if not lisans_kodu or not kayitli_makine_kodu:
                return False, "Lisans bilgileri eksik", None

            mevcut_makine_kodu = self.makine_kodu_uret()
            if mevcut_makine_kodu != kayitli_makine_kodu:
                return False, "Bu lisans başka bir bilgisayara ait", None

            response = requests.post(
                f"{self.sunucu}/kontrol",
                json={
                    "lisans_kodu": lisans_kodu,
                    "makine_kodu": kayitli_makine_kodu,
                },
                timeout=10,
                verify=self._verify_bundle(),
            )

            if response.status_code == 200:
                sonuc = response.json()
                if sonuc.get("durum") == "başarılı":
                    kayit["son_kontrol"] = datetime.now().isoformat()
                    try:
                        self._json_yaz(self.lisans_dosyasi, kayit)
                    except Exception:
                        pass
                    return True, "Lisans geçerli", sonuc
                return False, sonuc.get("mesaj", "Lisans geçersiz"), None

            return False, f"Sunucu hatası: {response.status_code}", None
        except requests.exceptions.ConnectionError:
            return self.son_bilinen_kontrol()
        except Exception as exc:
            return False, f"Kontrol hatası: {str(exc)}", None

    def son_bilinen_kontrol(self):
        """Internet yokken son bilinen lisans durumunu kontrol et."""
        try:
            kayit = self.lisans_yukle()
            if not kayit:
                return False, "Lisans bilgisi yok", None

            kayitli_makine_kodu = kayit.get("makine_kodu")
            mevcut_makine_kodu = self.makine_kodu_uret()
            if not kayitli_makine_kodu or mevcut_makine_kodu != kayitli_makine_kodu:
                return False, "Bu lisans başka bir bilgisayara ait", None

            kayit_tarihi = kayit.get("son_kontrol") or kayit.get("kayit_tarihi", "2000-01-01")
            try:
                tarih = datetime.fromisoformat(kayit_tarihi)
                gun_farki = (datetime.now() - tarih).days
                if gun_farki > self.OFFLINE_GRACE_DAYS:
                    return False, f"Lisans kontrolü için internet bağlantısı gerekli ({self.OFFLINE_GRACE_DAYS} gün geçmiş)", None
            except Exception:
                pass

            return True, "Çevrimdışı mod - son bilinen durum", {"kalan_gun": "?"}
        except Exception:
            return False, "Çevrimdışı kontrol başarısız", None


lisans = LisansYoneticisi()
