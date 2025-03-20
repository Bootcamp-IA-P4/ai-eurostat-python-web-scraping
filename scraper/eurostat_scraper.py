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
from datetime import datetime

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
            chrome_options.add_argument("--start-maximized")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-extensions")
            chrome_options.add_argument("--disable-software-rasterizer")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-infobars")
            chrome_options.add_argument('--no-proxy-server')
            chrome_options.add_argument("--proxy-server='direct://'")
            chrome_options.add_argument("--proxy-bypass-list=*")
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            
            if headless:
                chrome_options.add_argument("--headless=new")
            
            logger.info("Chrome options configured")
            
            # Configurar el servicio de Chrome
            service = Service(ChromeDriverManager().install())
            logger.info("Chrome service configured")
            
            # Crear el driver
            self.driver = webdriver.Chrome(
                service=service,
                options=chrome_options
            )
            self.driver.set_page_load_timeout(60)  # Aumentar timeout
            self.wait = WebDriverWait(self.driver, 20)  # Aumentar wait time
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
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            self.logger.info("Body element found")

            # Wait for the page to be fully loaded
            time.sleep(20)
            self.logger.info("Waited for page load")

            # Try to find the table with different selectors
            table = None
            selectors = [
                '.ag-root-wrapper',
                '.ag-theme-alpine',
                'div[class*="ag-root"]',
                'div[class*="ag-theme"]',
                '.ag-center-cols-container',
                '.ag-body-viewport'
            ]

            for selector in selectors:
                try:
                    table = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"Found table with selector: {selector}")
                    break
                except Exception as e:
                    self.logger.warning(f"Could not find table with selector {selector}: {str(e)}")
                    continue

            if not table:
                # Try to get page source for debugging
                page_source = self.driver.page_source
                self.logger.error(f"Page source length: {len(page_source)}")
                raise Exception("Could not find the table element")

            # Wait for data container
            data_container = None
            container_selectors = [
                '.ag-center-cols-container',
                '.ag-body-viewport',
                '.ag-body-container'
            ]

            for selector in container_selectors:
                try:
                    data_container = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    self.logger.info(f"Found data container with selector: {selector}")
                    break
                except:
                    continue

            if not data_container:
                raise Exception("Could not find the data container")

            # Initialize years list
            years = [str(year) for year in range(2015, 2025)]
            self.logger.info(f"Using years: {years}")

            # Define EU countries
            eu_countries = [
                'European Union', 'Euro area', 'Belgium', 'Bulgaria', 'Czechia', 'Denmark',
                'Germany', 'Estonia', 'Ireland', 'Greece', 'Spain', 'France', 'Croatia',
                'Italy', 'Cyprus', 'Latvia', 'Lithuania', 'Luxembourg', 'Hungary', 'Malta',
                'Netherlands', 'Austria', 'Poland', 'Portugal', 'Romania', 'Slovenia',
                'Slovakia', 'Finland', 'Sweden', 'Iceland', 'Liechtenstein', 'Norway',
                'Switzerland', 'Montenegro', 'North Macedonia', 'Albania', 'Serbia',
                'Türkiye', 'Bosnia and Herzegovina', 'Kosovo', 'Moldova', 'Ukraine'
            ]

            # Get all rows with multiple attempts
            rows = None
            row_selectors = ['.ag-row', '[role="row"]', '.ag-row-position-absolute']
            
            for selector in row_selectors:
                try:
                    rows = WebDriverWait(self.driver, 15).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    if rows:
                        self.logger.info(f"Found {len(rows)} rows with selector: {selector}")
                        break
                except:
                    continue

            if not rows:
                raise Exception("Could not find any rows")

            # Skip the header row
            rows = rows[1:] if len(rows) > 1 else []
            self.logger.info(f"Processing {len(rows)} data rows (excluding header)")

            processed_rows = []
            for row in rows:
                try:
                    # Get the country name from the first cell with multiple attempts
                    first_cell = None
                    cell_selectors = [
                        '.ag-cell[col-id="geo"]',
                        '.ag-cell-first-left-pinned',
                        '.ag-cell-last-left-pinned',
                        '[role="gridcell"]'
                    ]
                    
                    for selector in cell_selectors:
                        try:
                            first_cell = row.find_element(By.CSS_SELECTOR, selector)
                            if first_cell:
                                self.logger.info(f"Found first cell with selector: {selector}")
                                break
                        except:
                            continue
                    
                    if not first_cell:
                        raise Exception("Could not find the first cell")

                    country_text = first_cell.text.strip()
                    self.logger.info(f"Found country text: {country_text}")
                    
                    # Try to find a matching country/region
                    geo_area = None
                    for country in eu_countries:
                        if country_text.lower() == country.lower():
                            geo_area = country
                            break

                    if not geo_area:
                        self.logger.info(f"Skipping row, no valid country/region found in: {country_text}")
                        continue

                    # Initialize row_data
                    row_data = {'geo_area': geo_area}
                    for year in range(2015, 2025):
                        row_data[f'year_{year}'] = None

                    # Get values for each year with multiple attempts
                    for year in years:
                        try:
                            # Try different selectors for year cells
                            cell = None
                            year_cell_selectors = [
                                f'.ag-cell[col-id="{year}"]',
                                f'[role="gridcell"][col-id="{year}"]',
                                f'[aria-colindex="{int(year)-2014}"]',  # Assuming 2015 is index 1
                                f'.ag-cell[col-id="TIME_PERIOD"][col-value="{year}"]',
                                f'.ag-cell[col-id="value"][col-value="{year}"]',
                                f'.ag-cell[col-id="values"][col-value="{year}"]',
                                f'.ag-cell[col-id="value_{year}"]',
                                f'.ag-cell[col-id="values_{year}"]',
                                f'.ag-cell[col-id="TIME_PERIOD_{year}"]',
                                f'.ag-cell[col-id="value"][aria-colindex="{int(year)-2014}"]',
                                f'.ag-cell[col-id="values"][aria-colindex="{int(year)-2014}"]',
                                f'.ag-cell[col-id="TIME_PERIOD"][aria-colindex="{int(year)-2014}"]'
                            ]
                            
                            for selector in year_cell_selectors:
                                try:
                                    cell = row.find_element(By.CSS_SELECTOR, selector)
                                    if cell:
                                        self.logger.info(f"Found year cell with selector: {selector}")
                                        # Log the cell's attributes for debugging
                                        self.logger.info(f"Cell attributes: {cell.get_attribute('outerHTML')}")
                                        break
                                except Exception as e:
                                    self.logger.debug(f"Could not find cell with selector {selector}: {str(e)}")
                                    continue
                            
                            if cell:
                                cell_value = cell.text.strip()
                                # Remove any non-numeric characters except decimal point and minus sign
                                cell_value = re.sub(r'[^\d.-]', '', cell_value)
                                if cell_value:
                                    try:
                                        # Convert to float, handling any formatting issues
                                        value = float(cell_value.replace(',', ''))
                                        row_data[f'year_{year}'] = value
                                        self.logger.info(f"Found value for {geo_area}, year {year}: {value}")
                                    except ValueError as e:
                                        self.logger.warning(f"Could not convert value '{cell_value}' to float for {geo_area}, year {year}: {str(e)}")
                            else:
                                self.logger.warning(f"Could not find cell for {geo_area}, year {year}")
                        except Exception as e:
                            self.logger.warning(f"Error processing cell value for {geo_area}, year {year}: {str(e)}")
                            continue

                    processed_rows.append(row_data)
                    self.logger.info(f"Successfully processed row for {geo_area}")

                except Exception as e:
                    self.logger.error(f"Error processing row: {str(e)}")
                    continue

            if not processed_rows:
                raise Exception("No rows were successfully processed")

            self.logger.info(f"Successfully processed {len(processed_rows)} rows of data")
            return processed_rows

        except Exception as e:
            self.logger.error(f"Failed to extract table data: {str(e)}")
            # Try to get page source for debugging
            try:
                page_source = self.driver.page_source
                self.logger.error(f"Page source length: {len(page_source)}")
            except:
                pass
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

    def save_to_csv(self, data):
        """Save the scraped data to a CSV file"""
        if not data:
            self.logger.error("No data to save to CSV")
            return

        try:
            # Create DataFrame from the data
            df = pd.DataFrame(data)
            
            # Reorder columns to put geo_area first
            columns = ['geo_area'] + [f'year_{year}' for year in range(2015, 2025)]
            df = df[columns]
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'data/gdp_data_{timestamp}.csv'
            
            # Ensure data directory exists
            os.makedirs('data', exist_ok=True)
            
            # Save to CSV
            df.to_csv(filename, index=False)
            self.logger.info(f"Data saved to CSV file: {filename}")
            
            # Also save a copy without timestamp
            df.to_csv('data/gdp_data_latest.csv', index=False)
            self.logger.info("Data also saved as gdp_data_latest.csv")
            
        except Exception as e:
            self.logger.error(f"Error saving data to CSV: {str(e)}")

    def run_scraper(self):
        try:
            self.logger.info("Starting scraper run...")
            self.driver.get(self.base_url)
            self.logger.info("Successfully loaded URL")

            # Wait for initial load
            time.sleep(20)
            self.logger.info("Initial wait completed")

            # Extract data
            data = self.extract_table_data()
            if data:
                # Save to CSV first
                self.save_to_csv(data)
                # Then save to database
                self.save_data(data)
                self.logger.info("Data saved successfully")
            else:
                self.logger.error("Failed to extract table data")

        except Exception as e:
            self.logger.error(f"Error in scraper run: {str(e)}", exc_info=True)
        finally:
            self.cleanup()
            self.logger.info("Scraper run completed") 