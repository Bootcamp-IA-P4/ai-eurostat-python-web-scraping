from django.core.management.base import BaseCommand
from scraper.eurostat_scraper import EurostatScraper
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
        self.stdout.write('Starting Eurostat GDP data scraping...')
        
        try:
            with EurostatScraper(headless=options['headless']) as scraper:
                scraper.run_scraper()
            self.stdout.write(self.style.SUCCESS('Successfully scraped Eurostat GDP data'))
            
        except Exception as e:
            logger.error(f"Error in scraper execution: {str(e)}", exc_info=True)
            self.stdout.write(
                self.style.ERROR(f'Error scraping Eurostat data: {str(e)}')
            ) 