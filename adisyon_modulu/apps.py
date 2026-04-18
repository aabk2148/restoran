from django.apps import AppConfig
from django.core.signals import request_started
from django.db.models.signals import post_migrate


_startup_tasks_scheduled = False


ELAKI_ADMIN_THEME_CSS = """
:root {
    --admin-interface-header-background-color: #FFFFFF;
    --admin-interface-header-text-color: #17324A;
    --admin-interface-header-link-color: #1DA1A1;
    --admin-interface-header-link_hover-color: #0E2A47;
    --admin-interface-title-color: #17324A;
    --admin-interface-logo-color: #0E2A47;
    --admin-interface-module-background-color: #ffffff;
    --admin-interface-module-background-selected-color: #e7f8f6;
    --admin-interface-module-border-radius: 16px;
    --admin-interface-module-text-color: #17324a;
    --admin-interface-module-link-color: #1DA1A1;
    --admin-interface-module-link-selected-color: #0E2A47;
    --admin-interface-module-link-hover-color: #0E2A47;
    --admin-interface-generic-link-color: #1DA1A1;
    --admin-interface-generic-link-hover-color: #0E2A47;
    --admin-interface-generic-link-active-color: #0E2A47;
    --admin-interface-save-button-background-color: #0E2A47;
    --admin-interface-save-button-background-hover-color: #1DA1A1;
    --admin-interface-save-button-text-color: #ffffff;
    --admin-interface-delete-button-background-color: #9d2f45;
    --admin-interface-delete-button-background-hover-color: #7d2135;
    --admin-interface-delete-button-text-color: #ffffff;
    --admin-interface-related-modal-background-color: #0E2A47;
    --admin-interface-related-modal-background-opacity: 0.72;
    --admin-interface-related-modal-border-radius: 22px;
}

body.login {
    background:
        radial-gradient(circle at top, rgba(132, 215, 207, 0.22), transparent 28%),
        linear-gradient(135deg, #0E2A47 0%, #1DA1A1 100%) !important;
}

#header {
    background: #FFFFFF !important;
    color: #17324A !important;
    box-shadow: 0 12px 30px rgba(14, 42, 71, 0.20);
    border-bottom: 1px solid #D6E4E7;
}

#nav-sidebar {
    background: #FFFFFF !important;
    border-right: 1px solid #D6E4E7;
}

#site-name a,
#user-tools,
#user-tools a,
div.breadcrumbs,
div.breadcrumbs a {
    color: #17324A !important;
}

.module,
#changelist-filter,
.results,
.submit-row,
.dashboard .module {
    box-shadow: 0 16px 35px rgba(14, 42, 71, 0.10);
}

.button,
input[type=submit],
input[type=button],
.submit-row input,
a.button {
    border-radius: 999px !important;
    background: linear-gradient(135deg, #0E2A47 0%, #1DA1A1 100%) !important;
    border: 0 !important;
    box-shadow: 0 10px 24px rgba(14, 42, 71, 0.18);
}
""".strip()


class AdisyonModuluConfig(AppConfig):
    name = 'adisyon_modulu'

    def ready(self):
        post_migrate.connect(
            self._run_post_migrate_startup_tasks,
            sender=self,
            dispatch_uid='adisyon_modulu_post_migrate_startup',
        )
        request_started.connect(
            self._run_lazy_startup_tasks,
            dispatch_uid='adisyon_modulu_lazy_startup',
        )

    def _run_post_migrate_startup_tasks(self, **kwargs):
        self._sync_admin_interface_theme()

    def _run_lazy_startup_tasks(self, **kwargs):
        global _startup_tasks_scheduled

        if _startup_tasks_scheduled:
            return

        _startup_tasks_scheduled = True
        request_started.disconnect(
            self._run_lazy_startup_tasks,
            dispatch_uid='adisyon_modulu_lazy_startup',
        )
        self._sync_admin_interface_theme()
        self._start_backup_scheduler()

    def _sync_admin_interface_theme(self):
        try:
            from django.db import connection
            from django.db.utils import OperationalError, ProgrammingError
            from admin_interface.models import Theme
        except Exception:
            return

        try:
            if 'admin_interface_theme' not in connection.introspection.table_names():
                return

            theme = Theme.objects.filter(active=True).order_by('id').first()
            if theme is None:
                theme = Theme.objects.order_by('id').first()
            if theme is None:
                return

            field_names = {field.name for field in theme._meta.fields}
            desired_values = {
                'name': 'ELAKI',
                'active': True,
                'title': 'ELAKI Yonetim Paneli',
                'title_visible': True,
                'logo_visible': True,
                'css_header_background_color': '#0E2A47',
                'css_header_text_color': '#FFFFFF',
                'css_header_link_color': '#D7F6F4',
                'css_header_link_hover_color': '#FFFFFF',
                'css_module_background_color': '#FFFFFF',
                'css_module_background_selected_color': '#E7F8F6',
                'css_module_text_color': '#17324A',
                'css_module_link_color': '#1DA1A1',
                'css_module_link_selected_color': '#0E2A47',
                'css_module_link_hover_color': '#0E2A47',
                'css_generic_link_color': '#1DA1A1',
                'css_generic_link_hover_color': '#0E2A47',
                'css_generic_link_active_color': '#0E2A47',
                'css_save_button_background_color': '#0E2A47',
                'css_save_button_background_hover_color': '#1DA1A1',
                'css_save_button_text_color': '#FFFFFF',
                'css_delete_button_background_color': '#9D2F45',
                'css_delete_button_background_hover_color': '#7D2135',
                'css_delete_button_text_color': '#FFFFFF',
                'css_module_rounded_corners': True,
                'css_module_border_radius': '16px',
                'related_modal_background_color': '#0E2A47',
                'related_modal_background_opacity': '0.72',
                'related_modal_rounded_corners': True,
                'related_modal_close_button_visible': True,
                'list_filter_dropdown': True,
                'list_filter_sticky': True,
                'form_submit_sticky': True,
                'form_pagination_sticky': True,
                'css': ELAKI_ADMIN_THEME_CSS,
            }

            changed_fields = []
            for field_name, value in desired_values.items():
                if field_name not in field_names:
                    continue
                if getattr(theme, field_name) != value:
                    setattr(theme, field_name, value)
                    changed_fields.append(field_name)

            if not theme.active:
                theme.active = True
                if 'active' in field_names and 'active' not in changed_fields:
                    changed_fields.append('active')

            if changed_fields:
                if 'active' in field_names:
                    Theme.objects.exclude(pk=theme.pk).filter(active=True).update(active=False)
                theme.save(update_fields=changed_fields)

        except (OperationalError, ProgrammingError):
            return

    def _start_backup_scheduler(self):
        try:
            from .backup_scheduler import start_backup_scheduler
            start_backup_scheduler()
        except Exception:
            return
