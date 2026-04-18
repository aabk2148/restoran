from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("adisyon_modulu", "0016_personelpuantaj_menusiparistalebi_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="siparisitem",
            name="siparisi_alan",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="aldigi_siparisler",
                to=settings.AUTH_USER_MODEL,
                verbose_name="Siparisi Alan",
            ),
        ),
        migrations.AddField(
            model_name="siparisitem",
            name="son_siparis_hareketi",
            field=models.DateTimeField(blank=True, null=True, verbose_name="Son Siparis Hareketi"),
        ),
    ]
