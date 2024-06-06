from django.apps import AppConfig


class AdminmanagerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'adminmanager'

    def ready(self):
        import adminmanager.signals
