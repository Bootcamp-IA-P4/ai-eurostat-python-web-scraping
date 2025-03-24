from django.core.management.base import BaseCommand
from scraper.eurostat_scraper import EurostatScraper
from scraper.models import GeoArea, GDPData
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    """
    Django management command for scraping and importing GDP data from Eurostat.
    This command handles the complete ETL (Extract, Transform, Load) process:
    1. Extracts data using the EurostatScraper
    2. Transforms the raw scraped data
    3. Loads it into normalized database tables (GeoArea and GDPData)
    """
    help = 'Scrapes and imports GDP data from Eurostat into normalized database structure'

    def add_arguments(self, parser):
        """
        Define command-line arguments for this management command.
        
        Args:
            parser (argparse.ArgumentParser): Parser object to add arguments to
            
        Adds:
            --no-headless: Flag to run browser in visible mode (disabled headless mode)
        """
        parser.add_argument(
            '--no-headless',
            action='store_false',
            dest='headless',
            help='Run browser in visible mode (not headless)',
        )

    def handle(self, *args, **options):
        """
        Main entry point for the command. Executes the scraping and import process.
        
        Args:
            *args: Variable length argument list
            **options: Keyword arguments from command line
            
        Process Flow:
        1. Initialize scraper (with context manager for proper cleanup)
        2. Extract geographic metadata
        3. Extract GDP values
        4. Import all data to database
        5. Handle errors and report results
        """
        try:
            logger.info("0.Starting Eurostat GDP data import process")
            
            # Using context manager ensures proper scraper cleanup
            with EurostatScraper(headless=options.get('headless', True)) as scraper:
                # 1. Extract geographic metadata (region/country names and codes)
                logger.info("1.Getting geographic metadata")
                geo_title_dict_list = scraper.extract_table_data()
                
                if not geo_title_dict_list:
                    logger.error("1.1.No geographic metadata could be extracted")
                    raise Exception("No geographic metadata could be extracted")
                
                # 2. Extract all GDP values by year for each region
                logger.info("2.Extracting GDP data")
                gdp_data = scraper.extract_complete_gdp_data()
                
                if not gdp_data:
                    logger.error("2.1.No GDP data could be extracted")
                    raise Exception("No GDP data could be extracted")
                
                # 3. Process and import all data in a transaction
                logger.info("3.Importing data to database")
                self.import_data(geo_title_dict_list, gdp_data)
                
                logger.info(f"3.1.GDP data import completed successfully. Imported data for {len(geo_title_dict_list)} regions/countries")
                
        except Exception as e:
            logger.error(f"3.3.Error in GDP data import: {str(e)}", exc_info=True)
            raise  # Re-raise exception for Django to handle exit code

    def import_data(self, geo_dicts, gdp_data):
        """
        Import scraped data into database within a transaction.
        
        Args:
            geo_dicts (list): List of dictionaries containing geographic metadata
                            Format: [{'CODE1': 'Description1'}, {'CODE2': 'Description2'}, ...]
            gdp_data (dict): Nested dictionary containing GDP values by region and year
                            Format: {'row_id': {'year': {'value': x, 'flag': y, 'is_available': z}}}
                            
        Process:
        - Wraps all database operations in a single transaction
        - Processes each geographic area sequentially
        - Handles errors per region without failing entire import
        """
        with transaction.atomic():  # All or nothing transaction
            processed = 0  # Counter for successfully processed regions

            # Each geo_dict is a single-item dict like {'CODE': 'Description'}
            for geo_dict in geo_dicts:
                # Extract the single key-value pair from each dictionary
                for row_id, geo_info in geo_dict.items():
                    try:
                        self.process_geo_area(row_id, geo_info, gdp_data.get(row_id, {}))
                        processed += 1
                    except Exception as e:
                        # Log error but continue with next region
                        logger.error(f"Error processing area {row_id}: {str(e)}", exc_info=True)
                        continue

            logger.info(f"Successfully processed {processed} geographic areas")

    def process_geo_area(self, row_id, geo_name, year_data):
        """
        Process a single geographic area and its GDP data across years.
        
        Args:
            row_id (str): Unique identifier for the geographic area (e.g. 'AT' for Austria)
            geo_name (str): Descriptive name of the geographic area
            year_data (dict): GDP data for this area by year
                            Format: {'year': {'value': x, 'flag': y, 'is_available': z}}
                            
        1. GeoArea Handling:
           - Uses update_or_create to handle both new and existing regions
           - Sets special flags based on name content (EU, Euro area, Kosovo)
           - Handles Kosovo naming convention with UN resolution note
           
        2. GDPData Handling:
           - Processes each year's data separately
           - Uses update_or_create to maintain historical data
           - Converts year strings to integers
           - Preserves all metadata (flags, availability)
        """
        # Create or update geographic area with special flags
        geo_area, created = GeoArea.objects.update_or_create(
            code=row_id,
            defaults={
                'name': geo_name,
                'is_kosovo': 'Kosovo' in geo_name,  # Special Kosovo handling
                'is_eu': 'European Union' in geo_name,
                'is_euro_area': 'Euro area' in geo_name,
                'notes': 'UNSCR 1244/1999' if 'Kosovo*' in geo_name else None  # UN resolution note
            }
        )
        
        action = "Created" if created else "Updated"
        logger.debug(f"{action} geographic area: {row_id} - {geo_name}")
        
        # Process each year's GDP data for this region
        year_count = 0
        for year, value_info in year_data.items():
            try:
                GDPData.objects.update_or_create(
                    geo_area=geo_area,
                    year=int(year),  # Convert year string to integer
                    defaults={
                        'value': value_info['value'],
                        'flag': value_info['flag'],
                        'is_available': value_info['is_available']
                    }
                )
                year_count += 1
            except Exception as e:
                logger.warning(f"Error processing year {year} for area {row_id}: {str(e)}")
        
        logger.debug(f"Processed {year_count} years for area {row_id}")