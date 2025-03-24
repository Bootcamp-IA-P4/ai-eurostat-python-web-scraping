from django.db import models

class GeoArea(models.Model):
    """Almacena las áreas geográficas con sus metadatos"""
    code = models.CharField(max_length=20, unique=True)  # Ej: EU27_2020, EA, XK
    name = models.CharField(max_length=255)  # Nombre completo
    is_kosovo = models.BooleanField(default=False)
    is_eu = models.BooleanField(default=False)
    is_euro_area = models.BooleanField(default=False)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code} - {self.name}"

    class Meta:
        verbose_name = "Geographic Area"
        verbose_name_plural = "Geographic Areas"
        ordering = ['code']

class GDPData(models.Model):
    """Almacena los valores de GDP con sus metadatos"""
    geo_area = models.ForeignKey(GeoArea, on_delete=models.CASCADE, related_name='gdp_records')
    year = models.IntegerField()
    value = models.CharField(max_length=50, null=True, blank=True)  # Almacena el valor como string original
    
    # Flags de observación
    FLAG_CHOICES = [
        ('b', 'Break in time series'),
        ('p', 'Provisional'),
        ('e', 'Estimated'),
        (None, 'No flag'),
    ]
    flag = models.CharField(max_length=1, choices=FLAG_CHOICES, null=True, blank=True)
    is_available = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "GDP Data Record"
        verbose_name_plural = "GDP Data Records"
        unique_together = ('geo_area', 'year')
        ordering = ['geo_area__code', 'year']
    
    def __str__(self):
        status = "unavailable" if not self.is_available else f"{self.value}{f'({self.flag})' if self.flag else ''}"
        return f"{self.geo_area.code} [{self.year}]: {status}"