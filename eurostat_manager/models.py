from django.db import models

class GDPCategory(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField()
    icon_class = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "GDP Categories"

class GDPData(models.Model):
    category = models.ForeignKey(GDPCategory, on_delete=models.CASCADE, related_name='data')
    indicator = models.CharField(max_length=255)
    geo_area = models.CharField(max_length=100)
    time_period = models.CharField(max_length=50)
    value = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    unit = models.CharField(max_length=50)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.indicator} - {self.geo_area} - {self.time_period}"

    class Meta:
        verbose_name_plural = "GDP Data"
        indexes = [
            models.Index(fields=['category', 'indicator', 'geo_area', 'time_period']),
        ]

class GDPTableData(models.Model):
    indicator = models.CharField(max_length=255)
    unit = models.CharField(max_length=50, default='Million euro')
    geo_area = models.CharField(max_length=100, default='European Union')
    year_2019 = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    year_2020 = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    year_2021 = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    year_2022 = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    year_2023 = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    year_2024 = models.DecimalField(max_digits=15, decimal_places=2, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.indicator

    class Meta:
        verbose_name = "GDP Table Row"
        verbose_name_plural = "GDP Table Data" 