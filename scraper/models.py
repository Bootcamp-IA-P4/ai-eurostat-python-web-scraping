from django.db import models

class GeoArea(models.Model):
    """
    Represents a geographic area (country, region, or economic zone) with metadata.
    
    Key Attributes:
    - code: Unique identifier (e.g., 'EU27_2020', 'EA', 'XK')
    - name: Full descriptive name
    - is_kosovo: Flag for Kosovo (special political status)
    - is_eu: Flag for EU member states
    - is_euro_area: Flag for Eurozone members
    - notes: Additional contextual information
    
    The model automatically tracks creation and modification timestamps.
    """
    code = models.CharField(max_length=20, unique=True)  # Example: EU27_2020, EA, XK
    name = models.CharField(max_length=255)  # Full descriptive name
    is_kosovo = models.BooleanField(default=False)  # Special flag for Kosovo
    is_eu = models.BooleanField(default=False)  # European Union member flag
    is_euro_area = models.BooleanField(default=False)  # Euro area member flag
    notes = models.TextField(blank=True, null=True)  # For special cases like Kosovo's UN status
    created_at = models.DateTimeField(auto_now_add=True)  # Automatic creation timestamp
    updated_at = models.DateTimeField(auto_now=True)  # Automatic update timestamp
    
    def __str__(self):
        """String representation for admin interface and debugging"""
        return f"{self.code} - {self.name}"

    class Meta:
        """Metadata options for the GeoArea model"""
        verbose_name = "Geographic Area"  # Singular name in admin
        verbose_name_plural = "Geographic Areas"  # Plural name in admin
        ordering = ['code']  # Default ordering by area code

class GDPData(models.Model):
    """
    Stores GDP values with associated metadata and quality flags.
    
    Key Attributes:
    - geo_area: ForeignKey to GeoArea (parent region)
    - year: The reporting year
    - value: Original GDP value as string (preserves formatting)
    - flag: Data quality indicator (b=break, p=provisional, e=estimated)
    - is_available: Availability status
    
    The model includes automatic timestamps and enforces unique year-area combinations.
    """
    # Relationship to geographic area with CASCADE deletion (if area is deleted)
    geo_area = models.ForeignKey(
        GeoArea, 
        on_delete=models.CASCADE, 
        related_name='gdp_records'  # Accessor name for reverse relations
    )
    year = models.IntegerField()  # Reporting year as integer
    
    # Original GDP value stored as string to preserve formatting (e.g., decimals, spaces)
    value = models.CharField(max_length=50, null=True, blank=True)  
    
    # Data quality flags with predefined choices
    FLAG_CHOICES = [
        ('b', 'Break in time series'),  # Indicates methodological breaks
        ('p', 'Provisional'),  # Preliminary data subject to revision
        ('e', 'Estimated'),  # Expert estimation
        (None, 'No flag'),  # Default case
    ]
    flag = models.CharField(
        max_length=1, 
        choices=FLAG_CHOICES, 
        null=True, 
        blank=True
    )
    is_available = models.BooleanField(default=True)  # Data availability status
    
    # Automatic timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        """Metadata options for the GDPData model"""
        verbose_name = "GDP Data Record"  # Singular name in admin
        verbose_name_plural = "GDP Data Records"  # Plural name in admin
        unique_together = ('geo_area', 'year')  # Prevent duplicate year entries per area
        ordering = ['geo_area__code', 'year']  # Order by area code then year
    
    def __str__(self):
        """Human-readable representation showing availability/status"""
        status = ("unavailable" if not self.is_available 
                 else f"{self.value}{f'({self.flag})' if self.flag else ''}")
        return f"{self.geo_area.code} [{self.year}]: {status}"