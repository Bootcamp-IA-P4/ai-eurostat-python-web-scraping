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
from selenium.webdriver.common.action_chains import ActionChains
import pandas as pd
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
import csv
from django.db import transaction
from .models import GDPTableData # Importar el modelo de Django


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
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Desactivar el mensaje
            
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

    def scroll_horizontal(self, scrollable_div):
        """Realiza un scroll horizontal directo en un contenedor gestionado por JavaScript."""
        try:
            logger.info("Iniciando scroll horizontal directo en el contenedor...")
            
            # Verificar si el contenedor tiene scroll horizontal
            scroll_width = self.driver.execute_script("return arguments[0].scrollWidth", scrollable_div)
            visible_width = self.driver.execute_script("return arguments[0].clientWidth", scrollable_div)
            logger.info(f"scrollWidth: {scroll_width}, clientWidth: {visible_width}")
            
            if scroll_width <= visible_width:
                logger.warning("El contenedor no tiene scroll horizontal. No se realizará el scroll.")
                return
            
            # Mover el scroll directamente al final
            self.driver.execute_script("""
                arguments[0].scrollLeft = arguments[0].scrollWidth;
                arguments[0].dispatchEvent(new Event('scroll'));
            """, scrollable_div)
            logger.info("Scroll horizontal directo realizado correctamente (al final).")
            
            # Verificar la posición actual del scroll
            current_scroll = self.driver.execute_script("return arguments[0].scrollLeft", scrollable_div)
            logger.info(f"Posición actual del scroll después de mover al final: {current_scroll}px")
            
            # Opcional: Mover el scroll de vuelta al inicio
            self.driver.execute_script("""
                arguments[0].scrollLeft = 0;
                arguments[0].dispatchEvent(new Event('scroll'));
            """, scrollable_div)
            logger.info("Scroll horizontal directo realizado correctamente (al inicio).")
            
            # Verificar la posición actual del scroll
            current_scroll = self.driver.execute_script("return arguments[0].scrollLeft", scrollable_div)
            logger.info(f"Posición actual del scroll después de mover al inicio: {current_scroll}px")
            
        except Exception as e:
            logger.error(f"Error al realizar el scroll horizontal directo: {e}")


    def extract_visible_table_data(self):
        """Extrae los datos visibles de la tabla sin realizar scroll horizontal."""
        try:
            logger.info("Iniciando extracción de datos visibles de la tabla...")
            
            # Seleccionar las filas visibles de la tabla
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".ag-row")
            all_data = []  # Almacenar todos los datos extraídos
            
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, ".ag-cell")
                row_data = [cell.text.strip() for cell in cells]
                all_data.append(row_data)
            
            logger.info("Extracción de datos visibles completada.")
            return all_data
        except Exception as e:
            logger.error(f"Error al extraer los datos visibles de la tabla: {e}")
            return []
        
    def extract_table_data(self):
        """Extrae los datos de la tabla de la página con reintentos."""
        if not self.driver:
            logger.error("Driver no inicializado. No se pueden extraer datos.")
            return None, None  # Devuelve None para encabezados y datos

        try:
            logger.info("Iniciando extracción de datos de la tabla...")
            self.driver.get(self.base_url)
            logger.info("Página cargada correctamente.")
            # Aceptar cookies (si está presente)
            self.accept_cookies()
            # Esperar a que la tabla esté completamente cargada y sea clickeable
            self.wait_for_table_to_load()
            # Hacer scroll hasta la tabla
            logger.info("Haciendo scroll hasta la tabla...")
            table_element = self.driver.find_element(By.CSS_SELECTOR, "#estat-content-view-table")
            self.scroll_to_element(table_element)
            # Esperar un momento para que se carguen los datos después del scroll vertical
            time.sleep(2)
            # Extraer los headers de los años visibles
            logger.info("Extrayendo headers de los años visibles...")
            year_headers = self.driver.find_elements(By.CSS_SELECTOR, ".ag-header-group-cell .table-header-text")
            years = [header.text.strip() for header in year_headers if header.text.strip().isdigit()]
            logger.info(f"Años visibles extraídos: {years}")

            # Hacer scroll horizontal hasta la mitad para capturar el año 2019
            logger.info("Haciendo scroll horizontal hasta la mitad...")
            scrollable_div = self.driver.find_element(By.CSS_SELECTOR, ".ag-body-horizontal-scroll-viewport")
            scroll_width = self.driver.execute_script("return arguments[0].scrollWidth", scrollable_div)
            self.driver.execute_script(f"arguments[0].scrollLeft = {scroll_width // 3};", scrollable_div)
            logger.info("Scroll horizontal hasta la mitad realizado correctamente.")

            # Esperar un momento para que se carguen los datos después del scroll a la mitad
            time.sleep(5)

            # Extraer los headers de los años adicionales (incluyendo 2019)
            logger.info("Extrayendo headers de los años adicionales (hasta la mitad)...")
            additional_year_headers = self.driver.find_elements(By.CSS_SELECTOR, ".ag-header-group-cell .table-header-text")
            additional_years = [header.text.strip() for header in additional_year_headers if header.text.strip().isdigit()]
            logger.info(f"Años adicionales extraídos (hasta la mitad): {additional_years}")

            # Hacer scroll horizontal completo hacia la izquierda
            logger.info("Haciendo scroll horizontal completo hacia la izquierda...")
            self.driver.execute_script("arguments[0].scrollLeft = 0;", scrollable_div)
            logger.info("Scroll horizontal completo hacia la izquierda realizado correctamente.")

            # Esperar un momento para que se carguen los datos después del scroll completo
            time.sleep(2)

            # Extraer los headers de los años restantes
            logger.info("Extrayendo headers de los años restantes...")
            remaining_year_headers = self.driver.find_elements(By.CSS_SELECTOR, ".ag-header-group-cell .table-header-text")
            remaining_years = [header.text.strip() for header in remaining_year_headers if header.text.strip().isdigit()]
            logger.info(f"Años restantes extraídos: {remaining_years}")

            # Combinar y ordenar los años de menor a mayor
            all_years = list(set(years + additional_years + remaining_years))  # Eliminar duplicados
            all_years.sort()  # Ordenar de menor a mayor
            logger.info(f"Todos los años extraídos: {all_years}")

            # Filtrar los años para eliminar aquellos inferiores a 2019
            filtered_years = [year for year in all_years if int(year) >= 2019]
            logger.info(f"Años filtrados (>= 2019): {filtered_years}")

            # Extraer las cabeceras de la tabla (GEO y TIME)
            headers = self.driver.find_elements(By.CSS_SELECTOR, ".table-header-text")
            header_data = [header.text.strip() for header in headers if header.text.strip()]
            logger.info(f"Encabezados extraídos: {header_data}")

            # Extraer los datos de la tabla
            rows = self.driver.find_elements(By.CSS_SELECTOR, ".ag-row")
            data = []
            for row in rows:
                cells = row.find_elements(By.CSS_SELECTOR, ".ag-cell")
                row_data = [cell.text.strip() if cell.text.strip() else "" for cell in cells]  # Rellenar celdas en blanco
                data.append(row_data)
            logger.info(f"Se extrajeron {len(data)} filas de la tabla.")

            # Combinar los encabezados (TIME, GEO y años)
            final_headers = ["TIME", "GEO"] + filtered_years
            logger.info(f"Encabezados finales: {final_headers}")
            #Test
            print("TEST**Encabezados finales: ", final_headers)
            print("TEST**Datos: ", data)
            return header_data, data, filtered_years # Devuelve encabezados y datos por separado

        except Exception as e:
            logger.error(f"Error al extraer datos de la tabla: {e}", exc_info=True)
            return None, None
        
    def save_to_csv(self, headers, data, years, filename="output.csv"):
        """
        Guarda los datos en un CSV y en la base de datos.
        
        :param headers: Lista de cabeceras (TIME, GEO, años, países/regiones).
        :param data: Lista de listas con los datos de la tabla.
        :param filename: Nombre del archivo CSV.
        """
        try:
            # Extraer años y países/regiones dinámicamente
            # years = [h for h in headers if h.isdigit()]  # Años (elementos que son números)
            countries_regions = [h for h in headers if not h.isdigit() and h not in ["TIME", "GEO"]]  # Países/regiones
            #print("TEST**countries_regions: ", countries_regions)
            # Filtrar los datos para eliminar cabeceras y quedarnos solo con los valores
            clean_data = []
            for row in data:
                #Si la fila contiene valores numéricos, es una fila de datos
                if any(cell.replace(".", "").replace(" ", "").isdigit() for cell in row):
                    clean_data.append(row)

            # Depuración: Imprimir años, países/regiones y datos limpios
            print("Años:", years)
            #print("Países/Regiones:", countries_regions)
            #print("Datos limpios:", clean_data)
            #print("Número de filas limpias:", len(clean_data))

            # Verificar que countries_regions y clean_data tengan la misma longitud
            if len(countries_regions) != len(clean_data):
                logger.error(f"Error: countries_regions y clean_data no tienen la misma longitud.")
                logger.error(f"Países/Regiones: {len(countries_regions)}, Datos limpios: {len(clean_data)}")
                return

            # Crear la carpeta "data" si no existe
            os.makedirs("data", exist_ok=True)

            # Generar el nombre del archivo con fecha y hora
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"data/gdp_data_{timestamp}.csv"

            # Abrir el archivo CSV en modo escritura
            with open(filename, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)

                # Escribir la primera fila (TIME y años)
                time_row = ["TIME"] + years  # TIME + años
                writer.writerow(time_row)

                # Escribir la segunda fila (GEO y celdas vacías)
                geo_row = ["GEO"] + [""] * len(years)  # GEO + celdas vacías
                writer.writerow(geo_row)

                # Escribir los datos (países/regiones y valores)
                for i, row in enumerate(clean_data):
                    # Cada fila de datos comienza con el país/región y luego los valores
                    country_region = countries_regions[i]  # El país/región correspondiente
                    writer.writerow([country_region] + row)

            logger.info(f"Datos guardados en el archivo CSV: {filename}")

            # Guardar los datos en la base de datos
            self.save_to_db(countries_regions, clean_data, years)

        except Exception as e:
            logger.error(f"Error al guardar los datos en CSV o base de datos: {e}", exc_info=True)

    def save_to_db(self, countries_regions, clean_data, years):
        """
        Guarda los datos en la base de datos.
        
        :param countries_regions: Lista de países/regiones.
        :param clean_data: Lista de listas con los datos de la tabla.
        :param years: Lista de años.
        """
        try:
            # Crear un diccionario para mapear los años a los campos del modelo
            year_to_field = {
                "2019": "year_2019",
                "2020": "year_2020",
                "2021": "year_2021",
                "2022": "year_2022",
                "2023": "year_2023",
                "2024": "year_2024",
            }

            # Usar una transacción para garantizar la atomicidad
            with transaction.atomic():
                for i, row in enumerate(clean_data):
                    # Crear un diccionario con los datos para el modelo
                    gdp_data = {
                        "unit": "Million euro",
                        "geo_area": countries_regions[i],
                    }

                    # Asignar los valores de los años correspondientes
                    for j, year in enumerate(years):
                        if year in year_to_field:
                            field_name = year_to_field[year]
                            gdp_data[field_name] = float(row[j].replace(" ", "")) if row[j] else None

                    # Crear y guardar el objeto en la base de datos
                    GDPTableData.objects.create(**gdp_data)

            logger.info("Datos guardados en la base de datos correctamente.")
        except Exception as e:
            logger.error(f"Error al guardar los datos en la base de datos: {e}", exc_info=True)
            
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
