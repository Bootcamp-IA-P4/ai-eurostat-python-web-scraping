import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import os
from datetime import datetime

# Configurar logging para consola y archivo
log_file = "scraper.log"  # Nombre del archivo de log

# Crear el logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Nivel global de logging

# Formato de los logs
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler para el archivo
file_handler = logging.FileHandler(log_file, mode='a')
file_handler.setLevel(logging.DEBUG)  # Nivel de logging para el archivo
file_handler.setFormatter(formatter)

# Handler para la consola
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Nivel de logging para la consola
console_handler.setFormatter(formatter)

# Agregar los handlers al logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class EurostatScraper:
    def __init__(self, headless=True):
        self.base_url = "https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en&category=na10.nama10.nama_10_ma"
        self.driver = None
        self.headless = headless
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)

    def __enter__(self):
        """Inicializa el driver al entrar en el contexto."""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Cierra el driver al salir del contexto."""
        if self.driver:
            self.driver.quit()
            logger.info("Driver cerrado.")

    def setup_driver(self):
        """Configura el driver de Selenium."""
        try:
            chrome_options = Options()
            if self.headless:
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(60)
            self.wait = WebDriverWait(self.driver, 30)
        except Exception as e:
            self.capture_screenshot("setup_driver_error.png")
            logger.error(f"Error al configurar el driver: {e}")
            raise


    def extract_table_data(self):
        """Extrae los datos de la tabla de la página con reintentos."""
        max_attempts = 3  # Número máximo de intentos
        for attempt in range(max_attempts):
            try:
                self.driver.get(self.base_url)
                logger.info("Página cargada correctamente.")

                # Capturar una captura de pantalla después de cargar la página
                self.capture_screenshot("page_loaded")

                # Detectar captchas o restricciones
                self.detect_issues()

                # Aceptar cookies si el banner está presente
                try:
                    accept_cookies_button = self.wait.until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.wt-ecl-button:nth-child(1)"))
                    )
                    accept_cookies_button.click()
                    logger.info("Cookies aceptadas.")
                    self.capture_screenshot("cookies_accepted")
                except TimeoutException:
                    logger.warning("No se encontró el botón de aceptar cookies.")
                except Exception as e:
                    self.capture_screenshot("cookies_error")
                    logger.error(f"Error al intentar aceptar cookies: {e}")

                # Esperar a que la tabla esté presente
                self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".ag-theme-alpine")))
                logger.info("Tabla encontrada.")

                # Obtener el HTML de la tabla
                table_html = self.driver.find_element(By.CSS_SELECTOR, ".ag-theme-alpine").get_attribute("outerHTML")
                soup = BeautifulSoup(table_html, "html.parser")

                # Extraer filas de la tabla
                rows = soup.find_all("div", class_="ag-row")
                data = []
                for row in rows:
                    cells = row.find_all("div", class_="ag-cell")
                    row_data = [cell.text.strip() for cell in cells]
                    data.append(row_data)

                logger.info(f"Se extrajeron {len(data)} filas de la tabla.")
                return data

            except TimeoutException as e:
                if attempt < max_attempts - 1:  # Si no es el último intento
                    logger.warning(f"Intento {attempt + 1} fallido, reintentando...")
                    time.sleep(5)  # Espera antes de reintentar
                else:
                    self.capture_screenshot("timeout_error")
                    logger.error(f"Timeout al cargar la tabla después de {max_attempts} intentos: {e}")
                    raise
            except Exception as e:
                self.capture_screenshot("extract_table_data_error")
                logger.error(f"Error al extraer datos de la tabla: {e}")
                raise

    def capture_screenshot(self, filename):
        """Captura una captura de pantalla de la página actual con fecha y hora."""
        try:
            # Agregar fecha y hora al nombre del archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_with_timestamp = f"{filename}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename_with_timestamp)
            self.driver.save_screenshot(filepath)
            logger.info(f"Captura de pantalla guardada como: {filepath}")
        except Exception as e:
            logger.error(f"Error al capturar la pantalla: {e}")
    
    def detect_issues(self):
        if self.check_for_captcha() or self.check_for_restrictions():
            logger.error("Se detectaron problemas en la página (captcha o restricciones).")
            raise Exception("Captcha o restricciones detectadas.")

    def check_for_captcha(self):
            """Verifica si hay un captcha en la página."""
            try:
                captcha_element = self.driver.find_element(By.CSS_SELECTOR, "div.recaptcha-checkbox-border")
                if captcha_element:
                    logger.warning("Se detectó un captcha en la página.")
                    self.capture_screenshot("captcha_detected")
                    return True
            except Exception:
                logger.info("No se detectó captcha en la página.")
                return False

    def check_for_restrictions(self):
        try:
            # Buscar texto o elementos que indiquen restricciones
            body_text = self.driver.find_element(By.TAG_NAME, "body").text
            if "Access Denied" in body_text or "403 Forbidden" in body_text:
                logger.warning("Se detectó una restricción de acceso en la página.")
                self.capture_screenshot("access_restricted")
                return True
        except Exception:
            logger.info("No se detectaron restricciones de acceso.")
            return False
    
    def save_to_csv(self, data):
        """Guarda los datos extraídos en un archivo CSV."""
        if not data:
            logger.error("No hay datos para guardar.")
            return

        try:
            # Crear DataFrame
            df = pd.DataFrame(data[1:], columns=data[0])  # Usar la primera fila como encabezados
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/gdp_data_{timestamp}.csv"
            os.makedirs("data", exist_ok=True)
            df.to_csv(filename, index=False)
            logger.info(f"Datos guardados en el archivo CSV: {filename}")
        except Exception as e:
            self.capture_screenshot("save_to_csv_error.png")
            logger.error(f"Error al guardar los datos en CSV: {e}")

    def run(self):
        """Ejecuta el scraper."""
        try:
            data = self.extract_table_data()
            if data:
                self.save_to_csv(data)
            else:
                logger.error("No se pudieron extraer datos de la tabla.")
        except Exception as e:
            self.capture_screenshot("run_error.png")
            logger.error(f"Error al ejecutar el scraper: {e}")