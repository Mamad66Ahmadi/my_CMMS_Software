# work_orders/models/sequences.py
from django.db import models


class DocumentSequence(models.Model):
    code = models.CharField(max_length=50, unique=True)
    year = models.PositiveIntegerField()
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("code", "year")

    def __str__(self):
        return f"{self.code}-{self.year}: {self.last_number}"
