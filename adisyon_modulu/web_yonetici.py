import os
from ftplib import FTP
from jinja2 import Template

# --- AYARLARIN (SADECE BURAYI BİR KEZ DÜZENLE) ---
FTP_AYARLARI = {
    'host': 'ftp.elaki.net',
    'user': 'kullanici_adin',
    'pass': 'sifren',
    'web_klasor': '/public_html/laradatca'
}

def menuyu_gonder(kategoriler):
    # 1. HTML TASARIMI (Lara Datça Stili)
    html_sablonu = """
    <!DOCTYPE html>
    <html lang="tr">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Lara Datça Menü</title>
        <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600&family=Inter:wght@300;400;600&display=swap" rel="stylesheet">
        <style>
            :root { --bg-color: #fdfcf9; --text-main: #1c1c1c; --accent: #8b7355; }
            body { background-color: var(--bg-color); color: var(--text-main); font-family: 'Inter', sans-serif; margin: 0; padding-bottom: 50px; }
            .header { text-align: center; padding: 40px 20px; background: white; }
            .logo-container { width: 120px; height: 120px; margin: 0 auto 15px; border-radius: 20px; border: 2px solid var(--accent); display: flex; align-items: center; justify-content: center; overflow: hidden; background: white; }
            .logo-container img { width: 100%; height: 100%; object-fit: contain; padding: 10px; }
            .category-nav { position: sticky; top: 0; z-index: 1000; background: rgba(253, 252, 249, 0.95); backdrop-filter: blur(10px); padding: 15px 0; display: flex; overflow-x: auto; white-space: nowrap; border-bottom: 1px solid rgba(0,0,0,0.05); }
            .nav-item-btn { display: inline-block; padding: 8px 15px; margin: 0 5px; text-decoration: none; color: var(--text-main); font-size: 0.85rem; font-weight: 600; text-transform: uppercase; }
            .menu-container { max-width: 650px; margin: 0 auto; padding: 0 20px; }
            h2.category-title { font-family: 'Playfair Display', serif; text-align: center; font-size: 1.8rem; margin: 50px 0 30px; color: var(--accent); }
            .menu-item { display: flex; align-items: center; margin-bottom: 30px; gap: 15px; }
            .item-photo { width: 85px; height: 85px; border-radius: 12px; object-fit: cover; background: #eee; flex-shrink: 0; }
            .item-info { flex: 1; }
            .item-title-row { display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px dotted #ccc; }
            .item-name { font-weight: 600; text-transform: uppercase; font-size: 0.95rem; }
            .item-price { font-family: 'Playfair Display', serif; font-weight: 600; color: var(--accent); }
            .item-desc { font-size: 0.85rem; color: #666; margin-top: 5px; line-height: 1.3; }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="logo-container"><img src="logo.png"></div>
            <div style="letter-spacing: 3px; font-size: 0.8rem;">LARA DATÇA • MENÜ</div>
        </div>
        <div class="category-nav">
            {% for kat in kategoriler %}
                <a href="#kat-{{ kat.id }}" class="nav-item-btn">{{ kat.ad }}</a>
            {% endfor %}
        </div>
        <div class="menu-container">
            {% for kat in kategoriler %}
                <h2 class="category-title" id="kat-{{ kat.id }}">{{ kat.ad }}</h2>
                {% for urun in kat.urunler %}
                <div class="menu-item">
                    {% if urun.gorsel_adi %}
                        <img src="images/{{ urun.gorsel_adi }}" class="item-photo">
                    {% else %}
                        <div class="item-photo"></div>
                    {% endif %}
                    <div class="item-info">
                        <div class="item-title-row">
                            <span class="item-name">{{ urun.ad }}</span>
                            <span class="item-price">{{ urun.fiyat }} TL</span>
                        </div>
                        <div class="item-desc">{{ urun.aciklama }}</div>
                    </div>
                </div>
                {% endfor %}
            {% endfor %}
        </div>
    </body>
    </html>
    """
    
    # 2. HTML ÜRETİMİ
    sablon = Template(html_sablonu)
    cikti = sablon.render(kategoriler=kategoriler)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(cikti)
    
    # 3. FTP GÖNDERİMİ
    try:
        ftp = FTP(FTP_AYARLARI['host'])
        ftp.login(FTP_AYARLARI['user'], FTP_AYARLARI['pass'])
        ftp.cwd(FTP_AYARLARI['web_klasor'])
        
        # HTML'i at
        with open("index.html", "rb") as f:
            ftp.storbinary("STOR index.html", f)
            
        # Resimler klasörü (images) yoksa oluştur ve resimleri at
        try: ftp.mkd("images") 
        except: pass

        for kat in kategoriler:
            for urun in kat['urunler']:
                if urun.get('gorsel_yolu') and os.path.exists(urun['gorsel_yolu']):
                    with open(urun['gorsel_yolu'], "rb") as img:
                        ftp.storbinary(f"STOR images/{urun['gorsel_adi']}", img)
        
        ftp.quit()
        print("Menü başarıyla güncellendi!")
    except Exception as e:
        print(f"Hata: {e}")