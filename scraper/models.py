from django.db import models


class GDPTableData(models.Model):
    geo_area = models.CharField(max_length=500)
    unit = models.CharField(max_length=50, default='Million euro')
    year_2019 = models.CharField(max_length=50, null=True, blank=True)  # Cambiado a CharField
    year_2020 = models.CharField(max_length=50, null=True, blank=True)  # Cambiado a CharField
    year_2021 = models.CharField(max_length=50, null=True, blank=True)  # Cambiado a CharField
    year_2022 = models.CharField(max_length=50, null=True, blank=True)  # Cambiado a CharField
    year_2023 = models.CharField(max_length=50, null=True, blank=True)  # Cambiado a CharField
    year_2024 = models.CharField(max_length=50, null=True, blank=True)  # Cambiado a CharField
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.geo_area} - GDP"

    class Meta:
        verbose_name = "GDP Table Row"
        verbose_name_plural = "GDP Table Data"
