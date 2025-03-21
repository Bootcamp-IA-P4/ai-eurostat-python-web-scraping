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
    def handle(*args, **options):
        try:
            with EurostatScraper(headless=options.get('headless', True)) as scraper:
                scraper.run()
        except Exception as e:
            logger.error(f"Error scraping Eurostat data: {e}")