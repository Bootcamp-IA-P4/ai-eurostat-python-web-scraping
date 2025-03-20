from django.contrib import admin
from scraper.models import GDPCategory, GDPData, GDPTableData

@admin.register(GDPCategory)
class GDPCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'url', 'created_at', 'updated_at')
    search_fields = ('name',)

@admin.register(GDPData)
class GDPDataAdmin(admin.ModelAdmin):
    list_display = ('indicator', 'geo_area', 'time_period', 'value', 'unit', 'created_at')
    list_filter = ('category', 'geo_area', 'time_period', 'unit')
    search_fields = ('indicator', 'geo_area')

@admin.register(GDPTableData)
class GDPTableDataAdmin(admin.ModelAdmin):
    list_display = ('unit', 'geo_area', 'year_2019', 'year_2020', 'year_2021', 'year_2022', 'year_2023', 'year_2024')
    search_fields = ('geo_area',)
    list_filter = ('unit', 'geo_area') 