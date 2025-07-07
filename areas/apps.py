from django.apps import AppConfig


class AreasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'areas'
    
    def ready(self):
        import areas.signals  
