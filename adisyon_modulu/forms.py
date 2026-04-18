from django import forms

from .module_control import module_choices
from .models import HizliSatisCihaz, KullaniciProfili, ModulAyari, Masa, Sube, Yazici

MODULE_VISIBILITY_CHOICES = module_choices()

try:
    import win32print
except Exception:
    win32print = None


def windows_yazici_secimleri():
    if win32print is None:
        return []

    secimler = []
    bayrak = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
    for printer in win32print.EnumPrinters(bayrak):
        yazici_adi = printer[2]
        secimler.append((yazici_adi, yazici_adi))
    return sorted(set(secimler), key=lambda item: item[0].lower())


class YaziciAdminForm(forms.ModelForm):
    windows_yazici_adi = forms.ChoiceField(required=False, choices=[], label="Windows Yazici Adi")

    class Meta:
        model = Yazici
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        secimler = [("", "---------"), *windows_yazici_secimleri()]
        mevcut = self.initial.get("windows_yazici_adi") or getattr(self.instance, "windows_yazici_adi", "")
        if mevcut and (mevcut, mevcut) not in secimler:
            secimler.append((mevcut, mevcut))
        self.fields["windows_yazici_adi"].choices = secimler
        self.fields["windows_yazici_adi"].help_text = "Windows yazicisi secerseniz bu alani doldurun."
        self.fields["ip_adresi"].required = False
        for _, alan in self.fields.items():
            css = "form-select" if isinstance(alan.widget, forms.Select) else "form-control"
            alan.widget.attrs["class"] = css

    def clean(self):
        cleaned_data = super().clean()
        baglanti_tipi = cleaned_data.get("baglanti_tipi")

        if baglanti_tipi == "windows" and not cleaned_data.get("windows_yazici_adi"):
            self.add_error("windows_yazici_adi", "Windows yazici secimi zorunludur.")
        if baglanti_tipi == "ag" and not cleaned_data.get("ip_adresi"):
            self.add_error("ip_adresi", "IP / ag yazicisi icin IP adresi zorunludur.")
        return cleaned_data


class HizliSatisCihazAdminForm(forms.ModelForm):
    windows_yazici_adi = forms.ChoiceField(required=False, choices=[], label="Windows Yazici Adi")

    class Meta:
        model = HizliSatisCihaz
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        secimler = [("", "---------"), *windows_yazici_secimleri()]
        mevcut = self.initial.get("windows_yazici_adi") or getattr(self.instance, "windows_yazici_adi", "")
        if mevcut and (mevcut, mevcut) not in secimler:
            secimler.append((mevcut, mevcut))
        self.fields["windows_yazici_adi"].choices = secimler
        self.fields["windows_yazici_adi"].help_text = "Yazici tipi cihazlarda Windows yazicisi secebilirsiniz."
        self.fields["ip_adresi"].required = False
        for _, alan in self.fields.items():
            css = "form-select" if isinstance(alan.widget, forms.Select) else "form-control"
            alan.widget.attrs["class"] = css

    def clean(self):
        cleaned_data = super().clean()
        baglanti_tipi = cleaned_data.get("baglanti_tipi")
        cihaz_tipi = cleaned_data.get("cihaz_tipi")

        if cihaz_tipi == "yazici":
            if baglanti_tipi == "windows" and not cleaned_data.get("windows_yazici_adi"):
                self.add_error("windows_yazici_adi", "Windows yazici secimi zorunludur.")
            if baglanti_tipi == "ag" and not cleaned_data.get("ip_adresi"):
                self.add_error("ip_adresi", "IP / ag yazicisi icin IP adresi zorunludur.")
        return cleaned_data


class KullaniciProfiliAdminForm(forms.ModelForm):
    yonetim_paneli_modulleri = forms.MultipleChoiceField(
        required=False,
        choices=MODULE_VISIBILITY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Yonetim panelinde gorunecek moduller",
        help_text="Secili moduller kullanicinin panelinde gorunur. Hicbiri secilmezse panel kartlari gizlenir.",
    )

    class Meta:
        model = KullaniciProfili
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        mevcut = getattr(self.instance, "yonetim_paneli_modulleri", None)
        if mevcut is None:
            mevcut = [module_id for module_id, _ in MODULE_VISIBILITY_CHOICES]
        self.initial.setdefault("yonetim_paneli_modulleri", mevcut)


class ModulAyariAdminForm(forms.ModelForm):
    aktif_moduller = forms.MultipleChoiceField(
        required=False,
        choices=MODULE_VISIBILITY_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        label="Kullanima acik moduller",
        help_text="Sadece secili moduller uygulamada erisilebilir olur.",
    )

    class Meta:
        model = ModulAyari
        fields = "__all__"


class MasaEkleForm(forms.ModelForm):
    """Masa ekleme formu - yöneticiler tarafından kullanılan basit form"""

    class Meta:
        model = Masa
        fields = ['masa_no', 'kapasite']
        labels = {
            'masa_no': 'Masa Numarası',
            'kapasite': 'Kapasite (Kişi Sayısı)',
        }
        widgets = {
            'masa_no': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Örn: 1, 2A, VIP01',
                'maxlength': '10',
            }),
            'kapasite': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '100',
                'value': '4',
            }),
        }

    def clean_masa_no(self):
        masa_no = self.cleaned_data.get('masa_no', '').strip()
        if not masa_no:
            raise forms.ValidationError('Masa numarası boş olamaz.')
        return masa_no

    def clean_kapasite(self):
        kapasite = self.cleaned_data.get('kapasite')
        if kapasite and (kapasite < 1 or kapasite > 100):
            raise forms.ValidationError('Kapasite 1 ile 100 arasında olmalıdır.')
        return kapasite
