from django.contrib import admin
from scraper.models import GDPData, GeoArea

@admin.register(GeoArea)
class GeoAreaAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the GeoArea model.
    
    Key Features:
    - Displays key identification fields in list view
    - Allows filtering by political/economic groupings
    - Enables search by code or name
    - Maintains consistent ordering
    
    The decorator @admin.register replaces admin.site.register() for cleaner syntax.
    """
    # Fields to display in the list view (main admin table)
    list_display = ('code', 'name', 'is_kosovo', 'is_eu', 'is_euro_area')    
    # Filter options (right sidebar filters)
    list_filter = ('is_kosovo', 'is_eu', 'is_euro_area')    
    # Searchable fields (search box functionality)
    search_fields = ('code', 'name')    
    # Default sorting order
    ordering = ('code',)

@admin.register(GDPData)
class GDPDataAdmin(admin.ModelAdmin):
    """
    Admin interface configuration for the GDPData model.
    
    Key Features:
    - Shows the relationship to GeoArea plus temporal data
    - Filters by data quality flags and availability
    - Allows searching by geographic attributes or year
    - Orders data logically by location and chronology
    
    The admin interface handles the ForeignKey relationship automatically.
    """
    # Fields to display in the list view
    list_display = ('geo_area', 'year', 'value', 'flag', 'is_available')    
    # Filter options for data quality and availability
    list_filter = ('flag', 'is_available')    
    # Search configuration (includes related GeoArea fields)
    search_fields = ('geo_area__code', 'geo_area__name', 'year')    
    # Default sorting - by geographic code then chronologically
    ordering = ('geo_area__code', 'year')