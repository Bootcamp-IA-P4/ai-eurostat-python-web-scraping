from django.core.management.base import BaseCommand
from scraper.eurostat_scraper import EurostatScraper
from scraper.models import GeoArea, GDPData
import logging
from django.db import transaction

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrapes and imports GDP data from Eurostat into normalized database structure'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-headless',
            action='store_false',
            dest='headless',
            help='Run browser in visible mode (not headless)',
        )

    def handle(self, *args, **options):
        try:
            logger.info("0.Starting Eurostat GDP data import process")
            
            with EurostatScraper(headless=options.get('headless', True)) as scraper:
                # 1. Obtener metadatos geográficos
                logger.info("1.Getting geographic metadata")
                geo_title_dict_list = scraper.extract_table_data()
                
                if not geo_title_dict_list:
                    logger.error("1.1.No geographic metadata could be extracted")
                    raise Exception("No geographic metadata could be extracted")
                
                # 2. Obtener todos los datos GDP
                logger.info("2.Extracting GDP data")
                gdp_data = scraper.extract_complete_gdp_data()
                
                if not gdp_data:
                    logger.error("2.1.No GDP data could be extracted")
                    raise Exception("No GDP data could be extracted")
                
                # 3. Procesar e importar datos
                logger.info("3.Importing data to database")
                self.import_data(geo_title_dict_list, gdp_data)
                
                logger.info(f"3.1.GDP data import completed successfully. Imported data for {len(geo_title_dict_list)} regions/countries")
                
        except Exception as e:
            logger.error(f"3.3.Error in GDP data import: {str(e)}", exc_info=True)
            raise  # Re-lanzamos la excepción para que Django maneje el código de salida

    def import_data(self, geo_dicts, gdp_data):
        """Importa los datos a la base de datos"""
        with transaction.atomic():
            processed = 0

            for geo_dict in geo_dicts:  # Itera sobre cada diccionario dentro de la lista
                for row_id, geo_info in geo_dict.items():
                    try:
                        self.process_geo_area(row_id, geo_info, gdp_data.get(row_id, {}))
                        processed += 1
                    except Exception as e:
                        logger.error(f"Error processing area {row_id}: {str(e)}", exc_info=True)
                        continue

            logger.info(f"Successfully processed {processed} geographic areas")


    def process_geo_area(self, row_id, geo_name, year_data):
        """Procesa un área geográfica y sus datos GDP"""
        # Crear/actualizar área geográfica
        geo_area, created = GeoArea.objects.update_or_create(
            code=row_id,
            defaults={
                'name': geo_name,
                'is_kosovo': 'Kosovo' in geo_name,
                'is_eu': 'European Union' in geo_name,
                'is_euro_area': 'Euro area' in geo_name,
                'notes': 'UNSCR 1244/1999' if 'Kosovo*' in geo_name else None
            }
        )
        
        action = "Created" if created else "Updated"
        logger.debug(f"{action} geographic area: {row_id} - {geo_name}")
        
        # Procesar datos por año
        year_count = 0
        for year, value_info in year_data.items():
            try:
                GDPData.objects.update_or_create(
                    geo_area=geo_area,
                    year=int(year),
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