from django.apps import AppConfig


class SearchingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.listings'
    verbose_name = 'Advertising and search'

    def ready(self):
        from . import signals # noqa
