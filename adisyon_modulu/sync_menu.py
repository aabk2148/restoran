import psycopg2
import json

def menuyu_hazirla():
    try:
        # 1. PostgreSQL'e bağlan
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password="SENIN_SIFREN", # Buraya belirlediğin şifreyi yaz
            host="localhost",
            port="5432"
        )
        cur = conn.cursor()

        # 2. Verileri çek
        cur.execute("SELECT kategori, yemek_adi, aciklama, fiyat, alerjen_bilgisi, resim_yolu FROM menu_items WHERE aktif_mi = TRUE")
        rows = cur.fetchall()

        # 3. JSON formatına dönüştür
        menu_data = []
        for r in rows:
            menu_data.append({
                "kategori": r[0],
                "ad": r[1],
                "desc": r[2],
                "fiyat": float(r[3]),
                "alerjen": r[4],
                "img": r[5] if r[5] else "default.jpg"
            })

        # 4. JSON dosyası olarak kaydet (Web'e göndermeden önceki adım)
        with open('menu.json', 'w', encoding='utf-8') as f:
            json.dump(menu_data, f, ensure_ascii=False, indent=4)
        
        print("Menü başarıyla güncellendi! 'menu.json' hazır.")

    except Exception as e:
        print(f"Hata oluştu: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    menuyu_hazirla()