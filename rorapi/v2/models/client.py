from django.db import models
import uuid

class Client(models.Model):
    email = models.EmailField()
    client_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    last_request_at = models.DateTimeField(null=True, blank=True)
    request_count = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.email} - {self.client_id}"
