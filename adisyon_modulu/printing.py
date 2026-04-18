import socket

try:
    import win32print
except Exception:
    win32print = None


def windows_yazicilari_listele():
    if win32print is None:
        return []

    bayrak = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    return sorted({printer[2] for printer in win32print.EnumPrinters(bayrak)})


def yaziciya_veri_gonder(yazici, veri):
    baglanti_tipi = getattr(yazici, "baglanti_tipi", "ag") or "ag"
    if baglanti_tipi == "windows":
        return _windows_yaziciya_gonder(yazici.windows_yazici_adi, veri)
    return _ag_yaziciya_gonder(yazici.ip_adresi, yazici.port, veri)


def _ag_yaziciya_gonder(ip_adresi, port, veri):
    if not ip_adresi:
        raise ValueError("Ag yazicisi icin IP adresi zorunludur.")

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.settimeout(5)
        sock.connect((ip_adresi, int(port or 9100)))
        sock.sendall(veri)
    finally:
        sock.close()


def _windows_yaziciya_gonder(yazici_adi, veri):
    if win32print is None:
        raise RuntimeError("Windows yazici destegi icin pywin32 gerekli.")
    if not yazici_adi:
        raise ValueError("Windows yazici adi zorunludur.")

    handle = win32print.OpenPrinter(yazici_adi)
    try:
        job = ("ELAKI Raw Print", None, "RAW")
        win32print.StartDocPrinter(handle, 1, job)
        try:
            win32print.StartPagePrinter(handle)
            win32print.WritePrinter(handle, bytes(veri))
            win32print.EndPagePrinter(handle)
        finally:
            win32print.EndDocPrinter(handle)
    finally:
        win32print.ClosePrinter(handle)
