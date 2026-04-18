from django import template

register = template.Library()

@register.filter(name='tl_format')
def tl_format(value):
    """Sayıyı TL formatına çevirir (1.234,56 ₺)"""
    try:
        return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value

@register.filter
def sum_list(values, field):
    """Liste içindeki sözlüklerin belirli bir alanının toplamını hesaplar"""
    if not values:
        return 0
    total = 0
    for item in values:
        try:
            total += float(item.get(field, 0))
        except (ValueError, TypeError):
            pass
    return total

@register.filter
def cut(value, arg):
    """Metin içindeki karakteri kaldırır"""
    if value is None:
        return ""
    return str(value).replace(arg, '')

@register.filter
def divide(value, arg):
    """Bölme işlemi yapar"""
    try:
        return float(value) / float(arg)
    except (ValueError, ZeroDivisionError):
        return 0

@register.filter
def subtract(value, arg):
    """Çıkarma işlemi yapar"""
    try:
        return float(value) - float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def multiply(value, arg):
    """Çarpma işlemi yapar"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0

@register.filter
def add(value, arg):
    """Toplama işlemi yapar"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        return 0