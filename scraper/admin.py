from django.contrib import admin
from scraper.models import GDPData, GeoArea

@admin.register(GeoArea)
class GeoAreaAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_kosovo', 'is_eu', 'is_euro_area')
    list_filter = ('is_kosovo', 'is_eu', 'is_euro_area')
    search_fields = ('code', 'name')
    ordering = ('code',)

@admin.register(GDPData)
class GDPDataAdmin(admin.ModelAdmin):
    list_display = ('geo_area', 'year', 'value', 'flag', 'is_available')
    list_filter = ('flag', 'is_available')
    search_fields = ('geo_area__code', 'geo_area__name', 'year')
    ordering = ('geo_area__code', 'year')