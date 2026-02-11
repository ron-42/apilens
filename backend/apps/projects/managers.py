from django.db import models


class AppManager(models.Manager):
    def active(self):
        return self.filter(is_active=True)

    def for_user(self, user):
        return self.active().filter(owner=user)
