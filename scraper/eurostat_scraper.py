import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
from django.db import transaction
from scraper.models import GDPCategory, GDPData, GDPTableData
import os
import sys
import re

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

class EurostatScraper:
    def __init__(self, headless=True):
        self.logger = logging.getLogger(__name__)
        self.base_url = "https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en&category=na10.nama10.nama_10_ma"
        self.driver = None
        
        logger.info("Initializing EurostatScraper...")
        
        try:
            # Configure Chrome options
            chrome_options = Options()
            
            # Configuración básica
            chrome_options.add_argument("--start-maximized") # Maximize window
            chrome_options.add_argument("--no-sandbox") # Disable sandbox
            chrome_options.add_argument("--disable-dev-shm-usage") # Disable shared memory usage
            chrome_options.add_argument("--disable-gpu") # Disable GPU            
            chrome_options.add_argument("--disable-extensions") # Disable extensions
            chrome_options.add_argument("--remote-debugging-port=9222")  # Add debugging port
            chrome_options.add_argument("--disable-software-rasterizer")  # Disable software rasterizer
            
            if headless:
                chrome_options.add_argument("--headless=new")
                chrome_options.add_argument("--disable-gpu")  # Required for headless on some systems
            
            logger.info("Chrome options configured")
            
            # Configurar el servicio de Chrome con log level
            service = Service(
                ChromeDriverManager().install(),
                log_output=os.path.join(os.getcwd(), 'chromedriver.log')  # Add log file
            )
            logger.info("Chrome service configured")
            
            # Crear el driver con timeout más largo
            self.driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )
            self.driver.set_page_load_timeout(60)  # Increase timeout
            self.wait = WebDriverWait(self.driver, 20)  # Increase wait time
            logger.info("Chrome driver created successfully")
            
        except Exception as e:
            logger.error(f"Error initializing scraper: {str(e)}", exc_info=True)
            self.cleanup()
            raise

    def cleanup(self):
        """Método auxiliar para limpiar recursos"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.error(f"Error closing driver: {str(e)}")
            finally:
                self.driver = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def extract_table_data(self):
        try:
            # Wait for body to be present
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.logger.info("Body element found")

            # Wait for loading mask to disappear
            try:
                WebDriverWait(self.driver, 30).until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, '.loading-mask'))
                )
                self.logger.info("Loading mask disappeared")
            except TimeoutException:
                self.logger.warning("Loading mask timeout - proceeding anyway")

            # Wait for table to be present and visible
            table = WebDriverWait(self.driver, 45).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.ag-root-wrapper'))
            )
            self.logger.info("Found table")

            # Wait for data container with longer timeout
            data_container = WebDriverWait(self.driver, 45).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '.ag-center-cols-container'))
            )
            self.logger.info("Found data container")

            # Wait for data to be loaded
            time.sleep(10)  # Add extra wait time for data to load

            # Initialize years list with all years we want to capture
            years = [str(year) for year in range(2015, 2025)]
            self.logger.info(f"Using years: {years}")

            # Define a list of EU countries and territories in order
            eu_countries = [
                'European Union', 'Euro area', 'Belgium', 'Bulgaria', 'Czechia', 'Denmark',
                'Germany', 'Estonia', 'Ireland', 'Greece', 'Spain', 'France', 'Croatia',
                'Italy', 'Cyprus', 'Latvia', 'Lithuania', 'Luxembourg', 'Hungary', 'Malta',
                'Netherlands', 'Austria', 'Poland', 'Portugal', 'Romania', 'Slovenia',
                'Slovakia', 'Finland', 'Sweden', 'Iceland', 'Liechtenstein', 'Norway',
                'Switzerland', 'Montenegro', 'North Macedonia', 'Albania', 'Serbia',
                'Türkiye', 'Bosnia and Herzegovina', 'Kosovo', 'Moldova', 'Ukraine'
            ]

            # Try to scroll horizontally to see all columns
            try:
                scroll_container = self.driver.find_element(By.CSS_SELECTOR, '.ag-body-horizontal-scroll-viewport')
                # Scroll to the right
                self.driver.execute_script("arguments[0].scrollLeft = arguments[0].scrollWidth", scroll_container)
                time.sleep(2)
                # Scroll back to the left
                self.driver.execute_script("arguments[0].scrollLeft = 0", scroll_container)
                time.sleep(2)
            except Exception as e:
                self.logger.warning(f"Could not perform horizontal scroll: {str(e)}")

            # Get all rows and wait for them to be visible
            rows = WebDriverWait(self.driver, 20).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.ag-row'))
            )
            self.logger.info(f"Found {len(rows)} rows")

            # Try to find the GEO column by looking for a cell containing a known country
            geo_column_index = None
            for row in rows[:10]:  # Check only first 10 rows for efficiency
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, '.ag-cell')
                    self.logger.info(f"Row has {len(cells)} cells")
                    for i, cell in enumerate(cells):
                        cell_text = cell.text.strip()
                        self.logger.info(f"Cell {i} text: {cell_text}")
                        for country in eu_countries:
                            if cell_text.lower() == country.lower():
                                geo_column_index = i
                                self.logger.info(f"Found GEO column at index {i} with country {country}")
                                break
                        if geo_column_index is not None:
                            break
                    if geo_column_index is not None:
                        break
                except Exception as e:
                    self.logger.warning(f"Error processing row while searching for GEO column: {str(e)}")
                    continue

            if geo_column_index is None:
                # Try alternative approach: look for column header containing "GEO"
                header_cells = self.driver.find_elements(By.CSS_SELECTOR, '.ag-header-cell')
                for i, header in enumerate(header_cells):
                    if "GEO" in header.text.strip().upper():
                        geo_column_index = i
                        self.logger.info(f"Found GEO column at index {i} from header")
                        break

            if geo_column_index is None:
                self.logger.error("Could not find GEO column")
                return None

            # Get all column headers
            header_cells = self.driver.find_elements(By.CSS_SELECTOR, '.ag-header-cell')
            header_texts = [header.text.strip() for header in header_cells]
            self.logger.info(f"Found headers: {header_texts}")

            # Find year columns
            year_columns = {}
            for i, header in enumerate(header_texts):
                for year in years:
                    if year in header:
                        year_columns[year] = i
                        self.logger.info(f"Found column for year {year} at index {i}")

            processed_rows = []
            for row in rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, '.ag-cell')
                    if len(cells) <= geo_column_index:
                        continue

                    # Get the country name from the GEO column
                    geo_cell = cells[geo_column_index]
                    geo_text = geo_cell.text.strip()

                    # Try to find a matching country/region
                    geo_area = None
                    for country in eu_countries:
                        if geo_text.lower() == country.lower():
                            geo_area = country
                            break

                    # Skip if no valid country/region found
                    if not geo_area:
                        self.logger.info(f"Skipping row, no valid country/region found in: {geo_text}")
                        continue

                    # Initialize row_data with default values
                    row_data = {
                        'geo_area': geo_area,
                    }

                    # Initialize all years with None
                    for year in range(2015, 2025):
                        row_data[f'year_{year}'] = None

                    # Get values for each year from cells
                    for year, col_index in year_columns.items():
                        if col_index < len(cells):
                            try:
                                cell_value = cells[col_index].text.strip()
                                # Remove any non-numeric characters except decimal point and minus sign
                                cell_value = re.sub(r'[^\d.-]', '', cell_value)
                                # Convert to float if not empty
                                if cell_value:
                                    row_data[f'year_{year}'] = float(cell_value)
                                    self.logger.info(f"Found value for {geo_area}, year {year}: {cell_value}")
                            except (ValueError, IndexError) as e:
                                self.logger.warning(f"Error processing cell value for {geo_area}, year {year}: {str(e)}")
                                continue

                    processed_rows.append(row_data)
                    self.logger.info(f"Processed row for GEO: {geo_area} with years: {[f'{year}: {row_data[f'year_{year}']}'for year in range(2015, 2025)]}")

                except Exception as e:
                    self.logger.error(f"Error processing row: {str(e)}")
                    continue

            self.logger.info(f"Successfully processed {len(processed_rows)} rows of data")
            return processed_rows

        except Exception as e:
            self.logger.error(f"Failed to extract table data: {str(e)}")
            return None

    @transaction.atomic
    def save_data(self, data):
        if not data:
            self.logger.error("No data to save")
            return

        saved_count = 0
        for row in data:
            try:
                # Convert None values to 0 for database storage
                defaults = {}
                for year in range(2015, 2025):
                    year_key = f'year_{year}'
                    defaults[year_key] = row[year_key] if row[year_key] is not None else 0

                GDPTableData.objects.update_or_create(
                    geo_area=row['geo_area'],
                    defaults=defaults
                )
                saved_count += 1
            except Exception as e:
                self.logger.error(f"Error saving row data: {str(e)}")
                continue

        self.logger.info(f"Successfully saved {saved_count} data points")

    def run_scraper(self):
        try:
            self.logger.info("Starting scraper run...")
            self.driver.get(self.base_url)
            self.logger.info("Successfully loaded URL")

            # Wait for page to load with longer timeout and ensure table is fully loaded
            time.sleep(30)  # Give more time for initial load

            # Try to click on the dimension button first
            try:
                # Wait for the dimension button to be clickable
                dimension_button = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, 'button[title="Select dimension"]'))
                )
                dimension_button.click()
                time.sleep(2)
                self.logger.info("Clicked dimension button")

                # Try to find and click the GEO dimension
                geo_items = self.driver.find_elements(By.CSS_SELECTOR, '.ag-virtual-list-item')
                for item in geo_items:
                    if "GEO" in item.text:
                        item.click()
                        time.sleep(2)
                        break
                self.logger.info("Clicked GEO dimension")

                # Try to find the country list
                country_items = self.driver.find_elements(By.CSS_SELECTOR, '.ag-virtual-list-item')
                country_names = []
                for item in country_items:
                    text = item.text.strip()
                    self.logger.info(f"Found country item: {text}")
                    country_names.append(text)

                # Close the dimension panel
                close_button = self.driver.find_element(By.CSS_SELECTOR, 'button[aria-label="Close"]')
                close_button.click()
                time.sleep(2)

            except Exception as e:
                self.logger.warning(f"Could not interact with dimension menu: {str(e)}")

            # Scroll to ensure all content is loaded
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            self.driver.execute_script("window.scrollTo(0, 0);")
            time.sleep(5)

            # Extract and save data
            data = self.extract_table_data()
            if data:
                self.save_data(data)
                self.logger.info("Data saved successfully")
            else:
                self.logger.error("Failed to extract table data")

        except Exception as e:
            self.logger.error(f"Error in scraper run: {str(e)}", exc_info=True)
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception as e:
                    self.logger.error(f"Error closing driver: {str(e)}")
            self.logger.info("Scraper run completed") 