import json
import logging
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connections
from django.utils import timezone

from .models import KullaniciProfili, Masa, Sube, Urun

logger = logging.getLogger(__name__)


class YedeklemeYoneticisi:
    """Veritabani ve medya yedeklerini olusturur ve geri yukler."""

    def __init__(self, yedekleme_ayari):
        self.ayar = yedekleme_ayari
        self.zaman_damgasi = timezone.now().strftime("%Y%m%d_%H%M%S")
        self.dosya_adi = f"yedek_{self.zaman_damgasi}.zip"
        self.gecici_klasor = Path(tempfile.gettempdir()) / "restoran_yedekleme"
        self.gecici_klasor.mkdir(parents=True, exist_ok=True)

    def yedek_olustur(self):
        try:
            dosyalar, temizlenecekler = self._yedek_dosyalarini_hazirla()
            zip_yolu = self._zip_olustur(dosyalar)

            if self.ayar.yedekleme_tipi == "yerel":
                sonuc = self._yerel_kaydet(zip_yolu)
            else:
                sonuc = self._bulut_kaydet(zip_yolu)

            self._guvenli_sil(zip_yolu)
            for dosya in temizlenecekler:
                self._guvenli_sil(dosya)

            return sonuc
        except Exception as exc:
            logger.exception("Yedekleme hatasi")
            return {"basarili": False, "hata": str(exc)}

    def yedek_kapsamini_ozetle(self):
        media_root = Path(settings.MEDIA_ROOT)
        return [
            "Veritabani tam yedegi (PostgreSQL SQL dump, yoksa JSON snapshot)",
            "Ek JSON veri snapshoti (kullanicilar, masalar, urunler ve diger kayitlar icin ikinci katman)",
            f"Medya dosyalari ({self._dosya_sayisi(media_root)} dosya)",
            "Ortam ayarlari (.env)",
            "Statik dokuman ve gorseller (docs/images/logo dosyalari)",
            "Yedek manifesti ve degisiklik ozeti",
        ]

    def geri_yukle(self, yedek_zip_yolu):
        yedek_zip = Path(yedek_zip_yolu)
        if not yedek_zip.exists():
            return {"basarili": False, "hata": f"Yedek dosyasi bulunamadi: {yedek_zip}"}

        cikarma_klasoru = self.gecici_klasor / f"restore_{self.zaman_damgasi}"
        shutil.rmtree(cikarma_klasoru, ignore_errors=True)
        cikarma_klasoru.mkdir(parents=True, exist_ok=True)

        try:
            with zipfile.ZipFile(yedek_zip, "r") as arsiv:
                arsiv.extractall(cikarma_klasoru)

            veritabani_dosyasi = self._geri_yukleme_veritabani_dosyasini_bul(cikarma_klasoru)
            if veritabani_dosyasi is None:
                raise Exception("Yedek arsivinde veritabani dosyasi bulunamadi.")

            self._veritabanini_geri_yukle(veritabani_dosyasi)
            self._medyayi_geri_yukle(cikarma_klasoru / "media")
            self._tekil_dosyayi_geri_yukle(cikarma_klasoru / ".env", settings.BASE_DIR / ".env")
            self._dizini_geri_yukle(cikarma_klasoru / "static" / "docs", settings.BASE_DIR / "static" / "docs")
            self._dizini_geri_yukle(cikarma_klasoru / "static" / "images", settings.BASE_DIR / "static" / "images")
            self._tekil_dosyayi_geri_yukle(cikarma_klasoru / "static" / "logo.png", settings.BASE_DIR / "static" / "logo.png")
            self._tekil_dosyayi_geri_yukle(cikarma_klasoru / "static" / "elaki-logo.png", settings.BASE_DIR / "static" / "elaki-logo.png")
            self._tekil_dosyayi_geri_yukle(cikarma_klasoru / "app_assets" / "elaki.ico", settings.BASE_DIR / "elaki.ico")
            self._tekil_dosyayi_geri_yukle(cikarma_klasoru / "app_assets" / "elaki-pos.png", settings.BASE_DIR / "elaki-pos.png")
            return {"basarili": True, "dosya_adi": yedek_zip.name, "dosya_yolu": str(yedek_zip)}
        except Exception as exc:
            logger.exception("Geri yukleme hatasi")
            return {"basarili": False, "hata": str(exc)}
        finally:
            shutil.rmtree(cikarma_klasoru, ignore_errors=True)

    def mevcut_yedekleri_listele(self):
        klasor = self._hedef_yedek_klasoru()
        if not klasor.exists():
            return []

        yedekler = []
        for dosya in sorted(klasor.glob("yedek_*.zip"), key=os.path.getmtime, reverse=True):
            yedekler.append(
                {
                    "ad": dosya.name,
                    "yol": str(dosya),
                    "boyut": self._format_bytes(dosya.stat().st_size),
                    "tarih": timezone.datetime.fromtimestamp(
                        dosya.stat().st_mtime,
                        tz=timezone.get_current_timezone(),
                    ),
                }
            )
        return yedekler

    def _yedek_dosyalarini_hazirla(self):
        dosyalar = []
        temizlenecekler = []
        dosya_ozeti = {}

        db_yolu, db_arsiv_adi = self._veritabanini_yedekle()
        if db_yolu and db_arsiv_adi:
            dosyalar.append((db_arsiv_adi, db_yolu))
            temizlenecekler.append(db_yolu)
            dosya_ozeti.update(self._dosya_ozeti_ekle(db_arsiv_adi, db_yolu))

        json_snapshot = self._json_yedek_olustur("veritabani_snapshot")
        dosyalar.append(("veritabani_snapshot.json", json_snapshot))
        temizlenecekler.append(json_snapshot)
        dosya_ozeti.update(self._dosya_ozeti_ekle("veritabani_snapshot.json", json_snapshot))

        self._dizin_ekle(dosyalar, dosya_ozeti, Path(settings.MEDIA_ROOT), "media")
        self._dosya_ekle(dosyalar, dosya_ozeti, settings.BASE_DIR / ".env", ".env")
        self._dizin_ekle(dosyalar, dosya_ozeti, settings.BASE_DIR / "static" / "docs", "static/docs")
        self._dizin_ekle(dosyalar, dosya_ozeti, settings.BASE_DIR / "static" / "images", "static/images")
        self._dosya_ekle(dosyalar, dosya_ozeti, settings.BASE_DIR / "static" / "logo.png", "static/logo.png")
        self._dosya_ekle(dosyalar, dosya_ozeti, settings.BASE_DIR / "static" / "elaki-logo.png", "static/elaki-logo.png")
        self._dosya_ekle(dosyalar, dosya_ozeti, settings.BASE_DIR / "elaki.ico", "app_assets/elaki.ico")
        self._dosya_ekle(dosyalar, dosya_ozeti, settings.BASE_DIR / "elaki-pos.png", "app_assets/elaki-pos.png")

        manifest_yolu = self._manifest_olustur(db_arsiv_adi, dosya_ozeti)
        dosyalar.append(("manifest.json", manifest_yolu))
        temizlenecekler.append(manifest_yolu)
        dosya_ozeti.update(self._dosya_ozeti_ekle("manifest.json", manifest_yolu))

        return dosyalar, temizlenecekler

    def _veritabanini_yedekle(self):
        db_settings = settings.DATABASES["default"]
        engine = db_settings.get("ENGINE", "")

        if "postgresql" in engine:
            pg_dump = self._postgres_araci_bul("pg_dump")
            if pg_dump:
                return self._postgres_sql_yedegi_olustur(pg_dump, db_settings), "veritabani.sql"
            logger.warning("pg_dump bulunamadi, JSON yedek formatina geciliyor.")
            return self._json_yedek_olustur(), "veritabani.json"

        if "sqlite3" in engine:
            hedef = self.gecici_klasor / f"veritabani_{self.zaman_damgasi}.sqlite3"
            sqlite_path = Path(db_settings.get("NAME"))
            if sqlite_path.exists():
                shutil.copy2(sqlite_path, hedef)
                return hedef, "veritabani.sqlite3"

        return None, None

    def _postgres_sql_yedegi_olustur(self, pg_dump_path, db_settings):
        db_path = self.gecici_klasor / f"veritabani_{self.zaman_damgasi}.sql"
        env = os.environ.copy()
        env["PGPASSWORD"] = db_settings.get("PASSWORD", "") or ""
        subprocess.run(
            [
                str(pg_dump_path),
                "-h",
                str(db_settings.get("HOST", "localhost") or "localhost"),
                "-p",
                str(db_settings.get("PORT", "5432") or "5432"),
                "-U",
                str(db_settings.get("USER", "postgres") or "postgres"),
                "-d",
                str(db_settings.get("NAME", "")),
                "-f",
                str(db_path),
                "-c",
            ],
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
        return db_path

    def _json_yedek_olustur(self, on_ek="veritabani"):
        db_path = self.gecici_klasor / f"{on_ek}_{self.zaman_damgasi}.json"
        with open(db_path, "w", encoding="utf-8") as handle:
            call_command("dumpdata", format="json", indent=2, stdout=handle)
        return db_path

    def _manifest_olustur(self, db_arsiv_adi, dosya_ozeti):
        manifest_yolu = self.gecici_klasor / f"manifest_{self.zaman_damgasi}.json"
        onceki_manifest = self._onceki_manifesti_oku()
        veri = {
            "olusturma_tarihi": timezone.now().isoformat(),
            "yedekleme_tipi": self.ayar.yedekleme_tipi,
            "veritabani_dosyasi": db_arsiv_adi,
            "yedek_kapsami": self.yedek_kapsamini_ozetle(),
            "kritik_kayit_sayilari": {
                "sube": Sube.objects.count(),
                "masa": Masa.objects.count(),
                "urun": Urun.objects.count(),
                "kullanici": User.objects.count(),
                "kullanici_profili": KullaniciProfili.objects.count(),
                "media_dosya": self._dosya_sayisi(Path(settings.MEDIA_ROOT)),
            },
            "dosya_ozeti": dosya_ozeti,
            "degisiklik_ozeti": self._degisiklik_ozeti_hesapla(
                onceki_manifest.get("dosya_ozeti", {}) if onceki_manifest else {},
                dosya_ozeti,
            ),
        }
        manifest_yolu.write_text(json.dumps(veri, ensure_ascii=False, indent=2), encoding="utf-8")
        return manifest_yolu

    def _zip_olustur(self, dosyalar):
        zip_yolu = self.gecici_klasor / self.dosya_adi
        with zipfile.ZipFile(zip_yolu, "w", zipfile.ZIP_DEFLATED) as zipf:
            for arcname, dosya_yolu in dosyalar:
                zipf.write(dosya_yolu, arcname)
        return zip_yolu

    def _yerel_kaydet(self, zip_yolu):
        hedef_klasor = self._hedef_yedek_klasoru()
        hedef_yol = hedef_klasor / self.dosya_adi
        shutil.copy2(zip_yolu, hedef_yol)
        self._temizle_eski_yedekler(hedef_klasor)

        return {
            "basarili": True,
            "dosya_adi": self.dosya_adi,
            "dosya_yolu": str(hedef_yol),
            "boyut": os.path.getsize(hedef_yol),
        }

    def _temizle_eski_yedekler(self, klasor):
        yedekler = sorted(klasor.glob("yedek_*.zip"), key=os.path.getmtime, reverse=True)
        limit = max(1, int(self.ayar.max_yerel_yedek or 1))
        if int(self.ayar.zaman_araligi or 1) >= 7:
            limit = 1

        for yedek in yedekler[limit:]:
            self._guvenli_sil(yedek)
            logger.info("Eski yedek silindi: %s", yedek.name)

    def _bulut_kaydet(self, zip_yolu):
        return self._yerel_kaydet(zip_yolu)

    def _hedef_yedek_klasoru(self):
        adaylar = [Path(self.ayar.yerel_klasor), settings.BASE_DIR / "backups"]

        for klasor in adaylar:
            try:
                klasor.mkdir(parents=True, exist_ok=True)
                if not os.access(klasor, os.W_OK):
                    continue

                if str(klasor) != self.ayar.yerel_klasor:
                    self.ayar.yerel_klasor = str(klasor)
                    self.ayar.save(update_fields=["yerel_klasor"])
                return klasor
            except Exception:
                continue

        raise Exception("Yedek klasorune yazilamiyor. Lutfen gecerli bir klasor secin.")

    def _geri_yukleme_veritabani_dosyasini_bul(self, klasor):
        for dosya_adi in ("veritabani.sql", "veritabani.json", "veritabani.sqlite3"):
            aday = klasor / dosya_adi
            if aday.exists():
                return aday
        return None

    def _veritabanini_geri_yukle(self, veritabani_dosyasi):
        db_settings = settings.DATABASES["default"]
        engine = db_settings.get("ENGINE", "")
        connections.close_all()

        if veritabani_dosyasi.suffix == ".json":
            call_command("flush", interactive=False, verbosity=0)
            call_command("loaddata", str(veritabani_dosyasi), verbosity=0)
            return

        if "postgresql" in engine and veritabani_dosyasi.suffix == ".sql":
            psql = self._postgres_araci_bul("psql")
            if not psql:
                raise Exception("psql bulunamadi. PostgreSQL geri yukleme icin psql gerekli.")

            env = os.environ.copy()
            env["PGPASSWORD"] = db_settings.get("PASSWORD", "") or ""
            subprocess.run(
                [
                    str(psql),
                    "-h",
                    str(db_settings.get("HOST", "localhost") or "localhost"),
                    "-p",
                    str(db_settings.get("PORT", "5432") or "5432"),
                    "-U",
                    str(db_settings.get("USER", "postgres") or "postgres"),
                    "-d",
                    str(db_settings.get("NAME", "")),
                    "-f",
                    str(veritabani_dosyasi),
                ],
                env=env,
                check=True,
                capture_output=True,
                text=True,
            )
            return

        if "sqlite3" in engine and veritabani_dosyasi.suffix == ".sqlite3":
            hedef = Path(db_settings.get("NAME"))
            hedef.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(veritabani_dosyasi, hedef)
            return

        raise Exception("Bu yedek icin uygun otomatik geri yukleme akisi bulunamadi.")

    def _medyayi_geri_yukle(self, kaynak_media):
        if not kaynak_media.exists():
            return

        hedef_media = settings.BASE_DIR / "media"
        if hedef_media.exists():
            shutil.rmtree(hedef_media, ignore_errors=True)
        shutil.copytree(kaynak_media, hedef_media)

    def _dizini_geri_yukle(self, kaynak_dizin, hedef_dizin):
        kaynak_dizin = Path(kaynak_dizin)
        hedef_dizin = Path(hedef_dizin)
        if not kaynak_dizin.exists():
            return

        if hedef_dizin.exists():
            shutil.rmtree(hedef_dizin, ignore_errors=True)
        hedef_dizin.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(kaynak_dizin, hedef_dizin)

    def _tekil_dosyayi_geri_yukle(self, kaynak_dosya, hedef_dosya):
        kaynak_dosya = Path(kaynak_dosya)
        hedef_dosya = Path(hedef_dosya)
        if not kaynak_dosya.exists():
            return

        hedef_dosya.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(kaynak_dosya, hedef_dosya)

    def _postgres_araci_bul(self, arac_adi):
        adaylar = []
        bulundu = shutil.which(arac_adi)
        if bulundu:
            adaylar.append(Path(bulundu))

        paket_adayi = settings.BASE_DIR.parent / "postgresql" / "bin" / f"{arac_adi}.exe"
        if paket_adayi.exists():
            adaylar.append(paket_adayi)

        for taban in (Path("C:/Program Files/PostgreSQL"), Path("C:/Program Files (x86)/PostgreSQL")):
            if not taban.exists():
                continue
            adaylar.extend(sorted(taban.glob(f"*/bin/{arac_adi}.exe"), reverse=True))

        for aday in adaylar:
            if aday.exists():
                return aday
        return None

    def _format_bytes(self, value):
        boyut = float(value)
        for unit in ("B", "KB", "MB", "GB"):
            if boyut < 1024:
                return f"{boyut:.1f} {unit}"
            boyut /= 1024
        return f"{boyut:.1f} TB"

    def _guvenli_sil(self, dosya_yolu):
        try:
            Path(dosya_yolu).unlink(missing_ok=True)
        except Exception:
            logger.warning("Gecici dosya silinemedi: %s", dosya_yolu)

    def _dizin_ekle(self, dosyalar, dosya_ozeti, kaynak_dizin, hedef_on_ek):
        kaynak_dizin = Path(kaynak_dizin)
        if not kaynak_dizin.exists():
            return

        for root, _, files in os.walk(kaynak_dizin):
            for file_name in files:
                dosya_yolu = Path(root) / file_name
                rel_yol = dosya_yolu.relative_to(kaynak_dizin)
                arcname = f"{hedef_on_ek}/{rel_yol.as_posix()}"
                dosyalar.append((arcname, dosya_yolu))
                dosya_ozeti.update(self._dosya_ozeti_ekle(arcname, dosya_yolu))

    def _dosya_ekle(self, dosyalar, dosya_ozeti, dosya_yolu, arcname):
        dosya_yolu = Path(dosya_yolu)
        if not dosya_yolu.exists() or not dosya_yolu.is_file():
            return
        dosyalar.append((arcname, dosya_yolu))
        dosya_ozeti.update(self._dosya_ozeti_ekle(arcname, dosya_yolu))

    def _dosya_ozeti_ekle(self, arcname, dosya_yolu):
        dosya_yolu = Path(dosya_yolu)
        try:
            stat = dosya_yolu.stat()
            return {
                arcname: {
                    "boyut": stat.st_size,
                    "degisti": int(stat.st_mtime),
                }
            }
        except FileNotFoundError:
            return {}

    def _onceki_manifesti_oku(self):
        hedef_klasor = self._hedef_yedek_klasoru()
        for yedek in sorted(hedef_klasor.glob("yedek_*.zip"), key=os.path.getmtime, reverse=True):
            try:
                with zipfile.ZipFile(yedek, "r") as arsiv:
                    with arsiv.open("manifest.json") as handle:
                        return json.loads(handle.read().decode("utf-8"))
            except Exception:
                continue
        return None

    def _degisiklik_ozeti_hesapla(self, onceki_ozet, yeni_ozet):
        onceki = set(onceki_ozet.keys())
        yeni = set(yeni_ozet.keys())
        degisen = [
            yol for yol in (yeni & onceki)
            if onceki_ozet.get(yol) != yeni_ozet.get(yol)
        ]
        return {
            "yeni_dosya": len(yeni - onceki),
            "silinen_dosya": len(onceki - yeni),
            "degisen_dosya": len(degisen),
        }

    def _dosya_sayisi(self, klasor):
        klasor = Path(klasor)
        if not klasor.exists():
            return 0
        return sum(1 for yol in klasor.rglob("*") if yol.is_file())
