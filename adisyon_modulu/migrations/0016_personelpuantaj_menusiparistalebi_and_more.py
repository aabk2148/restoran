from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('adisyon_modulu', '0015_yazici_windows_destegi'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PersonelPuantaj',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tarih', models.DateField(default=django.utils.timezone.localdate)),
                ('giris_saati', models.DateTimeField(default=django.utils.timezone.now)),
                ('cikis_saati', models.DateTimeField(blank=True, null=True)),
                ('notu', models.TextField(blank=True, null=True, verbose_name='Not')),
                ('sube', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='puantaj_kayitlari', to='adisyon_modulu.sube')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='puantaj_kayitlari', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Personel Puantaj',
                'verbose_name_plural': 'Personel Puantajlari',
                'ordering': ['-giris_saati'],
            },
        ),
        migrations.CreateModel(
            name='MenuSiparisTalebi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('masa_no', models.CharField(max_length=20, verbose_name='Masa No')),
                ('durum', models.CharField(choices=[('Beklemede', 'Beklemede'), ('Onaylandi', 'Onaylandi'), ('Reddedildi', 'Reddedildi')], default='Beklemede', max_length=15)),
                ('musteri_notu', models.TextField(blank=True, null=True, verbose_name='Musteri Notu')),
                ('olusturma_zamani', models.DateTimeField(auto_now_add=True)),
                ('guncelleme_zamani', models.DateTimeField(auto_now=True)),
                ('onay_zamani', models.DateTimeField(blank=True, null=True)),
                ('red_sebebi', models.TextField(blank=True, null=True, verbose_name='Red Sebebi')),
                ('olusturan_ip', models.GenericIPAddressField(blank=True, null=True)),
                ('adisyon', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='menu_talepleri', to='adisyon_modulu.adisyon')),
                ('masa', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='menu_siparis_talepleri', to='adisyon_modulu.masa')),
                ('onaylayan', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='onaylanan_menu_siparis_talepleri', to=settings.AUTH_USER_MODEL)),
                ('sube', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='menu_siparis_talepleri', to='adisyon_modulu.sube')),
            ],
            options={
                'verbose_name': 'Menu Siparis Talebi',
                'verbose_name_plural': 'Menu Siparis Talepleri',
                'ordering': ['-olusturma_zamani'],
            },
        ),
        migrations.CreateModel(
            name='MenuSiparisTalepKalemi',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('adet', models.PositiveIntegerField(default=1)),
                ('ozel_istek', models.TextField(blank=True, null=True, verbose_name='Ozel Istek')),
                ('talep', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='kalemler', to='adisyon_modulu.menusiparistalebi')),
                ('urun', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='adisyon_modulu.urun')),
            ],
            options={
                'verbose_name': 'Menu Siparis Kalemi',
                'verbose_name_plural': 'Menu Siparis Kalemleri',
            },
        ),
    ]
