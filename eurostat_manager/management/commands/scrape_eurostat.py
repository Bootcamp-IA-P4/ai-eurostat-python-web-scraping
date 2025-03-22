from django.core.management.base import BaseCommand
from scraper.eurostat_scraper import EurostatScraper  # Ajusta la ruta de importación
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scrapes GDP data from Eurostat'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-headless',
            action='store_false',
            dest='headless',
            help='Run browser in visible mode (not headless)',
        )

    def handle(self, *args, **options):
        try:
            with EurostatScraper(headless=options.get('headless', True)) as scraper:
                # Extraer los datos de la tabla
                headers, data = scraper.extract_table_data()
                
                if headers and data:
                    # Guardar los datos en un archivo CSV
                    scraper.save_to_csv(headers, data)
                    self.stdout.write(self.style.SUCCESS("Datos extraídos y guardados correctamente."))
                else:
                    logger.error("No se pudieron extraer datos de la tabla.")
                    self.stdout.write(self.style.ERROR("No se pudieron extraer datos de la tabla."))
        except Exception as e:
            logger.error(f"Error scraping Eurostat data: {e}", exc_info=True)
            self.stdout.write(self.style.ERROR(f"Error scraping Eurostat data: {e}"))