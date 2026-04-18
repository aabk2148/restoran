from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('adisyon_modulu', '0018_kullaniciprofili_kvkk_onayi'),
    ]

    operations = [
        migrations.AddField(
            model_name='kullaniciprofili',
            name='yonetim_paneli_modulleri',
            field=models.JSONField(
                blank=True,
                default=None,
                help_text='Bos birakilirsa kullanici rolune uygun tum paneller gorunur.',
                null=True,
                verbose_name='Yonetim Paneli Modulleri',
            ),
        ),
    ]
