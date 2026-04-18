from django.db import migrations, models

import adisyon_modulu.module_control


class Migration(migrations.Migration):

    dependencies = [
        ('adisyon_modulu', '0019_kullaniciprofili_yonetim_paneli_modulleri'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModulAyari',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('aktif_moduller', models.JSONField(blank=True, default=adisyon_modulu.module_control.default_enabled_module_ids, help_text='Secili moduller uygulamada erisilebilir olur. Kapali moduller kodda dursa da kullanicilar ulasamaz.', verbose_name='Kullanima Acik Moduller')),
                ('guncellenme_zamani', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Modul Ayari',
                'verbose_name_plural': 'Modul Ayarlari',
            },
        ),
    ]
