from django.db import migrations, models


def init_liste_sirasi(apps, schema_editor):
    HizliSatisKasa = apps.get_model("adisyon_modulu", "HizliSatisKasa")
    qs = HizliSatisKasa.objects.order_by("sube_id", "kasa_no", "id")
    step = 10
    current = 0
    for kasa in qs:
        current += step
        if kasa.liste_sirasi == 0:
            HizliSatisKasa.objects.filter(pk=kasa.pk).update(liste_sirasi=current)


class Migration(migrations.Migration):

    dependencies = [
        ("adisyon_modulu", "0020_modulayari"),
    ]

    operations = [
        migrations.AddField(
            model_name="hizlisatiskasa",
            name="favori_bir",
            field=models.BooleanField(
                default=False,
                help_text="Şubede tek hesap varsayılan olur; kasa seçiminde ve raporlarda öncelik verilir.",
                verbose_name="Favori 1 (varsayılan kasa)",
            ),
        ),
        migrations.AddField(
            model_name="hizlisatiskasa",
            name="liste_sirasi",
            field=models.PositiveIntegerField(default=0, verbose_name="Listeleme sırası"),
        ),
        migrations.AlterModelOptions(
            name="hizlisatiskasa",
            options={
                "ordering": ["liste_sirasi", "kasa_no"],
                "verbose_name": "Hızlı Satış Kasası",
                "verbose_name_plural": "Hızlı Satış Kasaları",
                "unique_together": {("sube", "kasa_no")},
            },
        ),
        migrations.RunPython(init_liste_sirasi, migrations.RunPython.noop),
    ]
