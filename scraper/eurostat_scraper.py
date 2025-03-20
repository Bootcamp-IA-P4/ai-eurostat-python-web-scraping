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
from eurostat_manager.models import GDPCategory, GDPData, GDPTableData
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
        self.base_url = "https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en&category=na10.nama10.nama_10_ma"
        self.driver = None
        
        logger.info("Initializing EurostatScraper...")
        
        try:
            # Configure Chrome options
            chrome_options = Options()
            
            # Configuración básica
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-extensions")
            
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
            self.driver.set_page_load_timeout(30)
            self.wait = WebDriverWait(self.driver, 10)
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
        logger.info(f"Extracting data from {self.base_url}")
        try:
            self.driver.get(self.base_url)
            logger.info("Successfully loaded URL")
            
            # Esperar a que la página se cargue completamente
            self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Esperar a que desaparezca el indicador de carga
            try:
                self.wait.until(
                    EC.invisibility_of_element_located((By.CSS_SELECTOR, ".loading-mask"))
                )
            except TimeoutException:
                logger.warning("Loading mask timeout, continuing anyway")
            
            # Dar tiempo adicional para la carga dinámica
            time.sleep(20)
            
            # Intentar hacer scroll para asegurar que todo el contenido se carga
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(5)
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            logger.info("Waiting for table elements...")
            
            # Esperar y obtener la tabla
            try:
                # Esperar por el contenedor de datos
                data_container = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ag-center-cols-container"))
                )
                logger.info("Found data container")
                
                # Esperar por las cabeceras
                header_container = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ag-header-container"))
                )
                logger.info("Found header container")
            except TimeoutException:
                logger.error("Could not find table elements")
                return None
            
            # Obtener los años (encabezados de columna)
            header_cells = self.driver.find_elements(By.CSS_SELECTOR, ".ag-header-cell")
            years = []
            
            for cell in header_cells:
                try:
                    # Intentar obtener el texto del span interno
                    text_element = cell.find_element(By.CSS_SELECTOR, ".ag-header-cell-text")
                    text = text_element.text.strip()
                    logger.info(f"Found header text: {text}")
                    
                    if text.isdigit():
                        years.append(text)
                        logger.info(f"Added year: {text}")
                except Exception as e:
                    logger.debug(f"Error processing header cell: {str(e)}")
                    continue
            
            if not years:
                # Intentar obtener los años directamente del contenido
                header_row = header_container.get_attribute('textContent')
                logger.info(f"Header row content: {header_row}")
                
                # Buscar años en el texto completo
                potential_years = re.findall(r'20\d{2}', header_row)
                years = sorted(list(set(potential_years)))
                logger.info(f"Found years from text content: {years}")
            
            if not years:
                logger.error("No years found in table headers")
                return None
            
            # Obtener las filas de datos
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".ag-row")
            data = []
            
            for row in rows:
                try:
                    cells = row.find_elements(By.CSS_SELECTOR, ".ag-cell")
                    if len(cells) < 2:  # Asegurarse de que hay al menos indicador y un valor
                        continue
                    
                    indicator = cells[0].text.strip()
                    if not indicator:
                        continue
                    
                    row_data = {
                        'Indicator': indicator,
                        'Unit': 'Million euro',  # Valor por defecto
                        'Geo': 'European Union'  # Valor por defecto
                    }
                    
                    # Agregar valores por año
                    for year, cell in zip(years, cells[1:]):
                        value = cell.text.strip()
                        try:
                            row_data[year] = float(value.replace(',', '.')) if value and value != ':' else None
                        except ValueError:
                            row_data[year] = None
                    
                    data.append(row_data)
                    logger.info(f"Processed row for indicator: {indicator}")
                    
                except Exception as e:
                    logger.error(f"Error processing row: {str(e)}")
                    continue
            
            if not data:
                logger.error("No data rows found")
                return None
            
            logger.info(f"Successfully processed {len(data)} rows of data")
            return pd.DataFrame(data)
            
        except Exception as e:
            logger.error(f"Error extracting table data: {str(e)}")
            return None

    @transaction.atomic
    def save_data(self, dataframe):
        if dataframe is None or dataframe.empty:
            logger.warning("No data to save")
            return
        
        logger.info("Saving data to database")
        try:
            saved_count = 0
            for _, row in dataframe.iterrows():
                try:
                    # Crear un diccionario con los valores de los años
                    year_data = {}
                    for year in ['2019', '2020', '2021', '2022', '2023', '2024']:
                        if year in row:
                            year_data[f'year_{year}'] = row[year]
                    
                    # Crear o actualizar el registro
                    GDPTableData.objects.update_or_create(
                        indicator=row['Indicator'],
                        defaults={
                            'unit': row['Unit'],
                            'geo_area': row['Geo'],
                            **year_data
                        }
                    )
                    saved_count += 1
                except Exception as e:
                    logger.error(f"Error saving row data: {str(e)}")
                    continue
            
            logger.info(f"Successfully saved {saved_count} data points")
            
        except Exception as e:
            logger.error(f"Error in save_data: {str(e)}")

    def run_scraper(self):
        logger.info("Starting scraper run...")
        
        df = self.extract_table_data()
        if df is not None:
            self.save_data(df)
        else:
            logger.error("Failed to extract table data")
        
        logger.info("Scraper run completed") 