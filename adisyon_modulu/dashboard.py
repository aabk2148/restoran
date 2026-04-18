from django.db import models
from django.urls import reverse
from django.utils import timezone

from .models import Adisyon, Bolge, Rezervasyon, SiparisItem, Sube
from .module_control import enabled_module_ids, module_choices


COLOR_PRESETS = {
    'branch': {'start': '#ffffff', 'end': '#dff6f3', 'accent': '#1DA1A1', 'text': '#0E2A47'},
    'quick': {'start': '#0f766e', 'end': '#1DA1A1', 'accent': '#cffafe', 'text': '#ffffff'},
    'waiter': {'start': '#d97706', 'end': '#ea580c', 'accent': '#ffedd5', 'text': '#ffffff'},
    'chef': {'start': '#b45309', 'end': '#dc2626', 'accent': '#fde68a', 'text': '#ffffff'},
    'management': {'start': '#0E2A47', 'end': '#1DA1A1', 'accent': '#d7fffa', 'text': '#ffffff'},
    'reservation': {'start': '#155e75', 'end': '#0f766e', 'accent': '#ccfbf1', 'text': '#ffffff'},
    'reports': {'start': '#1e3a8a', 'end': '#0f766e', 'accent': '#dbeafe', 'text': '#ffffff'},
    'settings': {'start': '#334155', 'end': '#0f172a', 'accent': '#e2e8f0', 'text': '#ffffff'},
    'tool': {'start': '#ffffff', 'end': '#eef7f6', 'accent': '#1DA1A1', 'text': '#0E2A47'},
}

MODULE_VISIBILITY_CHOICES = module_choices()


def _user_role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return 'Yonetici'
    profil = getattr(user, 'profil', None)
    return getattr(profil, 'rol', None)


def _can_access(user, allowed_roles):
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _user_role(user) in allowed_roles


def _card(card_id, title, desc, icon, url, theme, badge=None, stat=None, module_id=None):
    palette = COLOR_PRESETS[theme]
    return {
        'id': card_id,
        'module_id': module_id or card_id,
        'title': title,
        'desc': desc,
        'icon': icon,
        'url': url,
        'badge': badge,
        'stat': stat,
        'start': palette['start'],
        'end': palette['end'],
        'accent': palette['accent'],
        'text': palette['text'],
        'theme': theme,
    }


def _allowed_module_ids(user):
    profil = getattr(user, 'profil', None)
    selected_ids = getattr(profil, 'yonetim_paneli_modulleri', None)
    if selected_ids is None:
        return None
    return set(selected_ids)


def _filter_cards_for_user(user, cards):
    allowed_module_ids = _allowed_module_ids(user)
    if allowed_module_ids is None:
        return cards
    return [card for card in cards if card['module_id'] in allowed_module_ids]


def build_dashboard_context(user):
    today = timezone.localdate()
    active_modules = enabled_module_ids()
    subeler = list(Sube.objects.all().order_by('ad'))
    kapali_adisyon_sayisi = Adisyon.objects.filter(durum='Kapali', acilis_zamani__date=today).count()
    bugunku_rezervasyon_sayisi = Rezervasyon.objects.filter(tarih=today).count()

    sube_cards = [
        _card(
            f'sube-{sube.id}',
            sube.ad,
            'Restoran operasyon ekranina git',
            'bi-shop',
            reverse('sube_detay', args=[sube.id]),
            'branch',
        )
        for sube in subeler
    ]

    index_blocks = []

    if _can_access(user, ['Yonetici']):
        index_blocks.append(
            _card(
                'management-home',
                'Yonetici Kontrol Paneli',
                'Operasyonu tek ekranda izle ve yonet',
                'bi-speedometer2',
                reverse('yonetim_paneli'),
                'management',
                stat='Canli Ozet',
            )
        )

    if _can_access(user, ['Yonetici', 'Asci']):
        index_blocks.append(
            _card('kitchen-panel', 'Asci Paneli', 'Mutfak ve hazirlama akisi', 'bi-egg-fried', reverse('mutfak_ana_sayfa'), 'chef')
        )

    if _can_access(user, ['Yonetici', 'Garson', 'Kasa']):
        index_blocks.append(
            _card('waiter-panel', 'Garson Paneli', 'Canli masa cagri takibi', 'bi-bell-fill', reverse('garson_paneli'), 'waiter')
        )

    index_blocks.append(
        _card('puantaj-panel', 'Personel Puantaj', 'Giris-cikis ve vardiya takibi', 'bi-person-badge-fill', reverse('puantaj_paneli'), 'tool')
    )

    if _can_access(user, ['Yonetici', 'Garson', 'Kasa']):
        index_blocks.append(
            _card('reservation-panel', 'Rezervasyon', 'Yeni kayit ve masa planlama', 'bi-calendar2-check-fill', reverse('rezervasyon_listesi'), 'reservation', stat=f'Bugun {bugunku_rezervasyon_sayisi}')
        )

    index_blocks.append(
        _card('quick-sale', 'Hizli Satis', 'Barkodlu satis ve kasa akisi', 'bi-upc-scan', reverse('kasa_secim'), 'quick', badge='Yeni')
    )

    if _can_access(user, ['Yonetici', 'Muhasebe', 'Kasa']):
        index_blocks.append(
            _card('reports-panel', 'Raporlar', 'Excel, PDF ve premium analizler', 'bi-bar-chart-line-fill', reverse('rapor_sayfasi'), 'reports', stat=f'Bugun {kapali_adisyon_sayisi} hesap')
        )

    management_tools = []

    if user.is_superuser:
        management_tools.extend([
            _card('system-admin', 'Sistem', 'Django admin ve genel sistem ayarlari', 'bi-gear-fill', reverse('admin:index'), 'tool'),
            _card('table-admin', 'Masa Yönetimi', 'Masaları ekle ve çıkar', 'bi-grid-3x3-gap-fill', reverse('masa_yonetim_listesi'), 'tool'),
            _card('barcode-admin', 'Barkod', 'Hizli satis urun yonetimi', 'bi-upc-scan', reverse('admin:adisyon_modulu_hizlisatisurun_changelist'), 'tool'),
        ])

    if _can_access(user, ['Yonetici']):
        management_tools.extend([
            _card('xml-transfer', 'XML Aktar', 'XML fatura ve stok aktarimi', 'bi-filetype-xml', reverse('xml_yukle'), 'tool'),
            _card('backup', 'Yedekleme', 'Veri yedekleme ve geri donus kayitlari', 'bi-cloud-arrow-up-fill', reverse('yedekleme_sayfasi'), 'tool'),
            _card('printer-management', 'Yazicilar', 'Ag ve Windows yazici tanimlari', 'bi-printer-fill', reverse('yazici_yonetimi'), 'tool'),
            _card('suppliers', 'Tedarikciler', 'Tedarik ve alim yonetimi', 'bi-truck', reverse('tedarikci_listesi'), 'tool'),
            _card('loyalty', 'Sadakat', 'Musteri profili ve sadakat ekranlari', 'bi-star-fill', reverse('musteri_ara'), 'tool'),
            _card('production', 'Uretim', 'Receteli uretim ve stok akis planlama', 'bi-tools', reverse('uretim_ekrani'), 'tool'),
        ])

    if _can_access(user, ['Yonetici', 'Muhasebe']):
        management_tools.extend([
            _card('products', 'Urunler', 'Urun kartlari ve menu yonetimi', 'bi-box-seam', reverse('urun_listesi'), 'tool'),
            _card('expense-entry', 'Gider', 'Masraf kaydi ve finans takibi', 'bi-cash-stack', reverse('gider_ekle'), 'tool'),
        ])

    if _can_access(user, ['Yonetici', 'Garson', 'Kasa']):
        management_tools.extend([
            _card('reservation-new', 'Rezervasyon Ekle', 'Hizli yeni rezervasyon olustur', 'bi-calendar-plus', reverse('rezervasyon_ekle'), 'tool'),
            _card('reservation-list', 'Rezervasyon Listesi', 'Tum rezervasyonlari goruntule', 'bi-calendar-check', reverse('rezervasyon_listesi'), 'tool'),
        ])

    region_cards = []
    if _can_access(user, ['Yonetici', 'Asci']) and 'kitchen-panel' in active_modules:
        bekleyen_siparisler = {
            row['urun__bolge_id']: row['toplam']
            for row in SiparisItem.objects.filter(
                adisyon__durum='Acik',
                hazir_mi=False,
                iptal_edildi=False,
                urun__bolge__isnull=False,
            ).values('urun__bolge_id').annotate(toplam=models.Count('id'))
        }
        for bolge in Bolge.objects.select_related('sube').order_by('sube__ad', 'ad'):
            region_cards.append(
                _card(
                    f'kitchen-region-{bolge.id}',
                    f'{bolge.ad} Bolgesi',
                    f'{bolge.sube.ad} icin canli bolge ekrani',
                    'bi-fire',
                    reverse('mutfak_ekrani_filtreli', args=[bolge.id]),
                    'chef',
                    stat=f"Bekleyen {bekleyen_siparisler.get(bolge.id, 0)}",
                    module_id='kitchen-panel',
                )
            )

    index_blocks = [card for card in index_blocks if card['module_id'] in active_modules]
    management_tools = [card for card in management_tools if card['module_id'] in active_modules]
    region_cards = [card for card in region_cards if card['module_id'] in active_modules]
    index_blocks = _filter_cards_for_user(user, index_blocks)
    management_tools = _filter_cards_for_user(user, management_tools)
    region_cards = _filter_cards_for_user(user, region_cards)
    management_tools.extend(region_cards)
    all_dashboard_cards = index_blocks + management_tools

    return {
        'sube_cards': sube_cards,
        'index_blocks': index_blocks,
        'management_index_block': None,
        'management_tools': management_tools,
        'all_dashboard_cards': all_dashboard_cards,
        'default_index_block_ids': [card['id'] for card in index_blocks],
        'default_management_block_ids': [card['id'] for card in management_tools],
        'yonetim_blocks': index_blocks + management_tools + sube_cards,
        'dashboard_summary': {
            'sube_sayisi': len(subeler),
            'bugunku_rezervasyon': bugunku_rezervasyon_sayisi,
            'bugunku_kapali_hesap': kapali_adisyon_sayisi,
        },
    }
