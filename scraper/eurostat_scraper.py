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
import pandas as pd
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler

# Configurar la carpeta de logs
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)  # Crear la carpeta si no existe

# Configurar logging para consola y archivo con rotación
log_file = os.path.join(log_dir, "scraper.log")  # Archivo de log en la carpeta logs

# Crear el logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Nivel global de logging

# Formato de los logs
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# Handler para el archivo con rotación
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)  # 5 MB por archivo, 3 copias de respaldo
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
        self.wait = None

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
        logger.info("Configurando el driver de Selenium...")
        try:
            chrome_options = Options()
            if self.headless:
                logger.info("Modo headless activado")
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            
            # Desactivar la carga de imágenes para mejorar el rendimiento
            chrome_options.add_experimental_option("prefs", {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            })
            
            # Agregar verificación de conectividad antes de intentar instalar el driver
            logger.info("Intentando instalar el ChromeDriver...")
            chrome_driver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriver instalado en: {chrome_driver_path}")
            
            # Configurar el servicio de ChromeDriver para guardar el log en la carpeta logs
            service = Service(chrome_driver_path)
            service.log_path = os.path.join("logs", "webdriver.log")  # Guardar el log en la carpeta logs
            
            # Inicializar el driver y establecer el timeout
            logger.info("Inicializando el driver de Chrome...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            if self.driver:
                logger.info("Driver de Chrome inicializado correctamente")
                self.driver.set_page_load_timeout(60)
                self.wait = WebDriverWait(self.driver, 30)
            else:
                logger.error("No se pudo inicializar el driver de Chrome")
                raise Exception("No se pudo inicializar el driver de Chrome")
                
        except Exception as e:
            logger.error(f"Error al configurar el driver: {e}")
            raise

    def scroll_to_element(self, element):
        """Scroll hasta que el elemento esté visible."""
        if not self.driver:
            logger.error("Driver no inicializado. No se puede hacer scroll.")
            return
            
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            logger.info("Scroll hasta el elemento completado.")
            time.sleep(2)  # Esperar a que la página se estabilice después del scroll
        except Exception as e:
            logger.error(f"Error al hacer scroll hasta el elemento: {e}")

    def scroll_down_page(self, pixels=500):
        """Scroll hacia abajo una cantidad específica de píxeles."""
        if not self.driver:
            logger.error("Driver no inicializado. No se puede hacer scroll.")
            return
            
        try:
            self.driver.execute_script(f"window.scrollBy(0, {pixels});")
            logger.info(f"Scroll hacia abajo {pixels}px completado.")
            time.sleep(1)  # Pequeña pausa para que la página responda
        except Exception as e:
            logger.error(f"Error al hacer scroll hacia abajo: {e}")

    def scroll_to_bottom(self):
        """Scroll hasta el final de la página."""
        if not self.driver:
            logger.error("Driver no inicializado. No se puede hacer scroll.")
            return
            
        try:
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            logger.info("Scroll hasta el final de la página completado.")
            time.sleep(2)  # Esperar a que la página se estabilice
        except Exception as e:
            logger.error(f"Error al hacer scroll hasta el final: {e}")

    def accept_cookies(self):
        """Acepta las cookies si el banner está presente."""
        try:
            logger.info("Buscando el botón de aceptar cookies...")
            accept_cookies_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.wt-ecl-button:nth-child(1)"))
            )
            accept_cookies_button.click()
            logger.info("Cookies aceptadas.")
            self.capture_screenshot("cookies_accepted")
        except TimeoutException:
            logger.warning("No se encontró el botón de aceptar cookies. Continuando sin aceptar cookies.")
        except Exception as e:
            self.capture_screenshot("cookies_error")
            logger.error(f"Error al intentar aceptar cookies: {e}")

    def wait_for_table_to_load(self):
        """Espera a que la tabla esté completamente cargada y sea clickeable."""
        try:
            logger.info("Esperando a que la tabla esté completamente cargada...")
            
            # Capturar una captura de pantalla antes de esperar la tabla
            self.capture_screenshot("before_wait_for_table")
            
            # Esperar a que la tabla esté presente usando el id
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#estat-content-view-table")))
            
            # Esperar a que la tabla sea clickeable
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#estat-content-view-table")))
            
            logger.info("Tabla completamente cargada y clickeable.")
            
            # Capturar una captura de pantalla después de esperar la tabla
            self.capture_screenshot("after_wait_for_table")
            
        except TimeoutException as e:
            logger.error(f"Timeout al esperar la carga de la tabla: {e}")
            self.capture_screenshot("timeout_error")
            raise
        except Exception as e:
            logger.error(f"Error al esperar la carga de la tabla: {e}")
            self.capture_screenshot("wait_for_table_error")
            raise

    def extract_table_data(self):
        """Extrae los datos de la tabla de la página con reintentos."""
        if not self.driver:
            logger.error("Driver no inicializado. No se pueden extraer datos.")
            return None
            
        max_attempts = 1  # Número máximo de intentos
        for attempt in range(max_attempts):
            try:
                logger.info(f"Intento {attempt + 1} de extraer los datos de la tabla...")
                self.driver.get(self.base_url)
                logger.info("Página cargada correctamente.")

                # Aceptar cookies (si está presente)
                self.accept_cookies()

                # Esperar a que la tabla esté completamente cargada y sea clickeable
                self.wait_for_table_to_load()

                # Capturar una captura de pantalla antes del scroll
                self.capture_screenshot("before_scroll")

                # Hacer scroll hasta la tabla
                logger.info("Haciendo scroll hasta la tabla...")
                table_element = self.driver.find_element(By.CSS_SELECTOR, "#estat-content-view-table")
                self.scroll_to_element(table_element)

                # Capturar una captura de pantalla después del scroll
                self.capture_screenshot("after_scroll")

                # Extraer los encabezados de la tabla
                headers = self.driver.find_elements(By.CSS_SELECTOR, ".ag-header-cell-text")
                header_data = [header.text for header in headers]
                logger.info(f"Encabezados extraídos: {header_data}")

                # Extraer las filas de la tabla
                rows = self.driver.find_elements(By.CSS_SELECTOR, ".ag-row")
                data = []
                for row in rows:
                    cells = row.find_elements(By.CSS_SELECTOR, ".ag-cell")
                    row_data = [cell.text if cell.text else "" for cell in cells]  # Rellenar celdas en blanco
                    data.append(row_data)
                logger.info(f"Se extrajeron {len(data)} filas de la tabla.")
                for d in data:
                    print(f"{d}")

                return data

            except TimeoutException as e:
                if attempt < max_attempts - 1:  # Si no es el último intento
                    logger.warning(f"Intento {attempt + 1} fallido por timeout, reintentando...")
                    time.sleep(5)  # Esperar antes de reintentar
                else:
                    self.capture_screenshot("timeout_error")
                    logger.error(f"Timeout al cargar la tabla después de {max_attempts} intentos: {e}")
                    raise
            except Exception as e:
                self.capture_screenshot("extract_table_data_error")
                logger.error(f"Error al extraer datos de la tabla: {e}", exc_info=True)  # Registrar el stacktrace completo
                raise

    def save_to_csv(self, data):
        """Guarda los datos extraídos en un archivo CSV."""
        if not data:
            logger.error("No hay datos para guardar.")
            return

        try:
            # Verificar si hay datos de encabezado
            if len(data) > 1:
                # Usar la primera fila como encabezados
                headers = data[0]
                rows = data[1:]
            else:
                # Si no hay encabezados, usar índices genéricos como columnas
                headers = [f"Column_{i}" for i in range(len(data[0]))]
                rows = data

            # Crear DataFrame
            df = pd.DataFrame(rows, columns=headers)
            
            # Crear la carpeta "data" si no existe
            os.makedirs("data", exist_ok=True)
            
            # Generar el nombre del archivo con fecha y hora
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/gdp_data_{timestamp}.csv"
            
            # Guardar el DataFrame en un archivo CSV
            df.to_csv(filename, index=False)
            logger.info(f"Datos guardados en el archivo CSV: {filename}")
            
        except Exception as e:
            logger.error(f"Error al guardar los datos en CSV: {e}", exc_info=True)

    def capture_screenshot(self, filename):
        """Captura una captura de pantalla de la página actual con fecha y hora."""
        if not self.driver:
            logger.error("No se puede capturar la pantalla: el driver no está inicializado.")
            return
            
        try:
            # Limitar el número de capturas de pantalla
            max_screenshots = 10
            screenshots = sorted(
                [f for f in os.listdir(self.screenshot_dir) if f.endswith(".png")],
                key=lambda x: os.path.getctime(os.path.join(self.screenshot_dir, x))
            )
            if len(screenshots) >= max_screenshots:
                oldest_screenshot = screenshots[0]
                os.remove(os.path.join(self.screenshot_dir, oldest_screenshot))
                logger.info(f"Se eliminó la captura más antigua: {oldest_screenshot}")

            # Agregar fecha y hora al nombre del archivo
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_with_timestamp = f"{filename}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename_with_timestamp)
            self.driver.save_screenshot(filepath)
            logger.info(f"Captura de pantalla guardada como: {filepath}")
        except Exception as e:
            logger.error(f"Error al capturar la pantalla: {e}")
