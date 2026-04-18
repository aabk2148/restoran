from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adisyon_modulu', '0017_siparisitem_siparisi_alan_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='kullaniciprofili',
            name='kvkk_onay_tarihi',
            field=models.DateTimeField(blank=True, null=True, verbose_name='KVKK Onay Tarihi'),
        ),
        migrations.AddField(
            model_name='kullaniciprofili',
            name='kvkk_onaylandi',
            field=models.BooleanField(default=False, verbose_name='KVKK Onaylandi'),
        ),
    ]
