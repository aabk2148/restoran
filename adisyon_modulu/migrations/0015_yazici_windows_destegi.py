from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adisyon_modulu', '0014_sube_kroki_arkaplan_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='yazici',
            name='baglanti_tipi',
            field=models.CharField(choices=[('ag', 'IP / Ag Yazicisi'), ('windows', 'Windows Yazicisi')], default='ag', max_length=20, verbose_name='Bağlantı Tipi'),
        ),
        migrations.AddField(
            model_name='yazici',
            name='windows_yazici_adi',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Windows Yazıcı Adı'),
        ),
        migrations.AlterField(
            model_name='yazici',
            name='ip_adresi',
            field=models.GenericIPAddressField(blank=True, null=True, verbose_name='Yazıcı IP'),
        ),
        migrations.AddField(
            model_name='hizlisatiscihaz',
            name='baglanti_tipi',
            field=models.CharField(choices=[('ag', 'IP / Ag Yazicisi'), ('windows', 'Windows Yazicisi')], default='ag', max_length=20, verbose_name='Bağlantı Tipi'),
        ),
        migrations.AddField(
            model_name='hizlisatiscihaz',
            name='windows_yazici_adi',
            field=models.CharField(blank=True, max_length=255, null=True, verbose_name='Windows Yazıcı Adı'),
        ),
    ]
