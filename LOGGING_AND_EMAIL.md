## Hata Loglama ve E-Posta Bildirimi

Uygulama artik iki ana log dosyasi uretir:

- `logs/debug.log`: genel uygulama ve sunucu loglari
- `logs/errors.log`: 500 hatalari ve yakalanmayan exception kayitlari

Her hata kaydinda su bilgiler bulunur:

- `request_id`
- HTTP method
- istek yolu
- durum kodu
- istemci IP adresi
- kullanici adi

### Mail bildirimi nasil acilir

`app/.env` icine once mail alanlarini doldurun. Test etmeye hazir oldugunuzda `ERROR_EMAIL_ENABLED=True` yapin:

```env
ERROR_EMAIL_ENABLED=True
DJANGO_ADMINS=Senin Adin:seninmailin@example.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=seninmailin@gmail.com
EMAIL_HOST_PASSWORD=uygulama-sifresi
DEFAULT_FROM_EMAIL=Elaki Restoran <seninmailin@gmail.com>
SERVER_EMAIL=Elaki Restoran <seninmailin@gmail.com>
EMAIL_SUBJECT_PREFIX=[Elaki Restoran]
```

### Gmail icin not

Normal hesap sifresi yerine Gmail `App Password` kullanin. 2 adimli dogrulama acik olmali.

### Log dosyalari nerede?

Kurulu sistemde tipik konum:

`C:\ProgramData\ElakiRestoranPOS\app\logs\`

### Donen log ayari

- varsayilan dosya boyutu: `10 MB`
- varsayilan yedek sayisi: `10`

Isterseniz `.env` icinde bunlari degistirebilirsiniz:

```env
LOG_MAX_BYTES=10485760
LOG_BACKUP_COUNT=10
```
