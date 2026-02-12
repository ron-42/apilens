from django.db import models


class EndpointManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)

    def for_app(self, app):
        return self.active().filter(app=app)
