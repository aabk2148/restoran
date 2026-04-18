from decimal import Decimal
from xml.etree import ElementTree as ET

from adisyon_modulu.models import StokKalemi, StokHareket

NS = {
    "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
    "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
}


def get_text(node, path):
    el = node.find(path, NS)
    return el.text.strip() if el is not None and el.text else None


def find_text_multi(node, paths):
    for path in paths:
        value = get_text(node, path)
        if value:
            return value
    return None


def to_decimal(val):
    try:
        return Decimal(str(val).replace(",", "."))
    except Exception:
        return Decimal("0")


def stok_bul(ad, barkod=None):
    stok = None

    if barkod:
        stok = StokKalemi.objects.filter(barkod=barkod).first()

    if not stok and ad:
        stok = StokKalemi.objects.filter(ad__icontains=ad).first()

    return stok


def xml_fatura_aktar(path):
    with open(path, "rb") as f:
        raw = f.read()

    if not raw or not raw.strip():
        raise ValueError("Yüklenen dosya boş görünüyor.")

    # encoding çözme
    try:
        icerik = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        try:
            icerik = raw.decode("iso-8859-9")
        except UnicodeDecodeError:
            icerik = raw.decode("utf-8", errors="ignore")

    if not icerik.strip():
        raise ValueError("Dosya içeriği okunamadı veya boş.")

    try:
        root = ET.fromstring(icerik)
    except ET.ParseError as e:
        raise ValueError(f"Geçerli bir XML okunamadı: {e}")

    eklenen = []
    eslesmeyen = []

    satirlar = root.findall(".//cac:InvoiceLine", NS)

    if not satirlar:
        raise ValueError("XML içinde InvoiceLine satırı bulunamadı.")

    for line in satirlar:
        # ÜRÜN ADI (çoklu deneme)
        urun_adi = find_text_multi(line, [
            "cac:Item/cbc:Name",
            ".//cac:Item/cbc:Name",
            ".//cbc:Name",
            "cbc:Name",
        ])

        # MİKTAR
        miktar = to_decimal(find_text_multi(line, [
            "cbc:InvoicedQuantity",
            ".//cbc:InvoicedQuantity",
            "cbc:CreditedQuantity",
            ".//cbc:CreditedQuantity",
        ]))

        # FİYAT
        fiyat = to_decimal(find_text_multi(line, [
            "cac:Price/cbc:PriceAmount",
            ".//cac:Price/cbc:PriceAmount",
            ".//cbc:PriceAmount",
            ".//cbc:LineExtensionAmount",
        ]))

        # BARKOD / KOD
        barkod = find_text_multi(line, [
            "cac:Item/cac:StandardItemIdentification/cbc:ID",
            ".//cac:StandardItemIdentification/cbc:ID",
            ".//cac:SellersItemIdentification/cbc:ID",
            ".//cac:ManufacturersItemIdentification/cbc:ID",
        ])

        stok = stok_bul(urun_adi, barkod)

        # ❌ eşleşmedi
        if not stok:
            print("ESLESMEDI:", {
                "urun_adi": urun_adi,
                "barkod": barkod,
                "miktar": miktar,
                "fiyat": fiyat,
    })
            eslesmeyen.append({
                "urun_adi": urun_adi or "Ürün adı okunamadı",
                "barkod": barkod or "",
                "miktar": str(miktar),
                "fiyat": str(fiyat),
    })
            continue

        # ✅ stok güncelle
        onceki = stok.miktar
        yeni = onceki + miktar

        stok.miktar = yeni
        stok.save()

        # hareket kaydı
        StokHareket.objects.create(
            stok=stok,
            tip="giris",
            miktar=miktar,
            onceki_miktar=onceki,
            sonraki_miktar=yeni,
            aciklama=f"XML fatura girişi - {urun_adi or stok.ad}",
        )

        eklenen.append({
            "urun_adi": urun_adi or stok.ad,
            "miktar": str(miktar),
            "fiyat": str(fiyat),
        })

    return eklenen, eslesmeyen