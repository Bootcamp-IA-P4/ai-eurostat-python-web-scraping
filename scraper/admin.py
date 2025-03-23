from django.contrib import admin
from scraper.models import GDPTableData

@admin.register(GDPTableData)
class GDPTableDataAdmin(admin.ModelAdmin):
    list_display = ('unit', 'geo_area', 'year_2019', 'year_2020', 'year_2021', 'year_2022', 'year_2023', 'year_2024')
    search_fields = ('geo_area',)
    list_filter = ('unit', 'geo_area') 