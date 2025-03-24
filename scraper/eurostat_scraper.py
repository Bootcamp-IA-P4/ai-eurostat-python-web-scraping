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
from .models import GeoArea, GDPData


# Configure logs directory
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)  # Create directory if it doesn't exist

# Configure logging for both console and rotating file
log_file = os.path.join(log_dir, "scraper.log")  # Log file in logs directory

# Create logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Global logging level

# Log format
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# File handler with rotation
file_handler = RotatingFileHandler(log_file, maxBytes=5 * 1024 * 1024, backupCount=3)  # 5 MB per file, 3 backups
file_handler.setLevel(logging.DEBUG)  # Logging level for file
file_handler.setFormatter(formatter)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)  # Logging level for console
console_handler.setFormatter(formatter)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(console_handler)

class EurostatScraper:
    def __init__(self, headless=True):
        """
        Initialize the scraper with default settings.
        Args:
            headless (bool): Whether to run browser in headless mode
        """
        self.base_url = "https://ec.europa.eu/eurostat/databrowser/view/nama_10_gdp/default/table?lang=en&category=na10.nama10.nama_10_ma"
        self.driver = None
        self.headless = headless
        self.screenshot_dir = "screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self.wait = None

    def __enter__(self):
        """Initialize driver when entering context"""
        self.setup_driver()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Clean up driver when exiting context"""
        if self.driver:
            self.driver.quit()
            logger.info("Driver closed.")

    def setup_driver(self):
        """Configure Selenium WebDriver with Chrome options"""
        logger.info("Setting up Selenium driver...")
        try:
            chrome_options = Options()
            if self.headless:
                logger.info("Headless mode enabled")
                chrome_options.add_argument("--headless=new")
            chrome_options.add_argument("--disable-gpu")
            chrome_options.add_argument("--disable-dev-shm-usage")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--window-size=1920,1080")
            chrome_options.add_argument("--disable-notifications")
            chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # Disable automation warning
            
            # Disable image loading for better performance
            chrome_options.add_experimental_option("prefs", {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2
            })
            
            # Verify connectivity before installing driver
            logger.info("Attempting to install ChromeDriver...")
            chrome_driver_path = ChromeDriverManager().install()
            logger.info(f"ChromeDriver installed at: {chrome_driver_path}")
            
            # Configure ChromeDriver service to save logs in logs directory
            service = Service(chrome_driver_path)
            service.log_path = os.path.join("logs", "webdriver.log")
            
            # Initialize driver with timeout settings
            logger.info("Initializing Chrome driver...")
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            if self.driver:
                logger.info("Chrome driver initialized successfully")
                self.driver.set_page_load_timeout(60)
                self.wait = WebDriverWait(self.driver, 30)
            else:
                logger.error("Failed to initialize Chrome driver")
                raise Exception("Failed to initialize Chrome driver")
                
        except Exception as e:
            logger.error(f"Error configuring driver: {e}")
            raise

    def _scroll_to_element(self, element):
        """
        Scroll until element is visible in viewport
        Args:
            element: WebElement to scroll to
        """
        if not self.driver:
            logger.error("Driver not initialized. Cannot scroll.")
            return            
        try:
            self.driver.execute_script("arguments[0].scrollIntoView(true);", element)
            logger.info("Scrolled to element.")
            time.sleep(2)  # Wait for page to stabilize after scrolling
        except Exception as e:
            logger.error(f"Error scrolling to element: {e}")

    def accept_cookies(self):
        """Accept cookies if banner is present"""
        try:
            logger.info("Looking for cookie accept button...")
            accept_cookies_button = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a.wt-ecl-button:nth-child(1)")))
            accept_cookies_button.click()
            logger.info("Cookies accepted.")
            self.capture_screenshot("cookies_accepted")
        except TimeoutException:
            logger.warning("Cookie accept button not found. Continuing without accepting cookies.")
        except Exception as e:
            self.capture_screenshot("cookies_error")
            logger.error(f"Error accepting cookies: {e}")

    def wait_for_table_to_load(self):
        """Wait for table to be fully loaded and clickable"""
        try:
            logger.info("Waiting for table to fully load...")            
            # Take screenshot before waiting for table
            self.capture_screenshot("before_wait_for_table")            
            # Wait for table to be present using ID
            self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#estat-content-view-table")))            
            # Wait for table to be clickable
            self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#estat-content-view-table")))            
            logger.info("Table fully loaded and clickable.")            
            # Take screenshot after table loads
            self.capture_screenshot("after_wait_for_table")
        except TimeoutException as e:
            logger.error(f"Timeout waiting for table to load: {e}")
            self.capture_screenshot("timeout_error")
            raise
        except Exception as e:
            logger.error(f"Error waiting for table to load: {e}")
            self.capture_screenshot("wait_for_table_error")
            raise

    def _scroll_horizontal_to_middle(self, scrollable_div):
        """
        Scroll horizontally to middle of table
        Args:
            scrollable_div: The scrollable container element
        """
        logger.info("Scrolling horizontally to middle...")
        scroll_width = self.driver.execute_script("return arguments[0].scrollWidth", scrollable_div)
        self.driver.execute_script(f"arguments[0].scrollLeft = {scroll_width // 3};", scrollable_div)
        time.sleep(5)
        logger.info("Horizontal scroll to middle completed")

    def _scroll_horizontal_to_start(self, scrollable_div):
        """
        Scroll horizontally to start (leftmost)
        Args:
            scrollable_div: The scrollable container element
        """
        logger.info("Scrolling horizontally to start...")
        self.driver.execute_script("arguments[0].scrollLeft = 0;", scrollable_div)
        time.sleep(5)
        logger.info("Horizontal scroll to start completed")

    def _extract_visible_years(self):
        """Extract currently visible year headers from table"""
        year_headers = self.driver.find_elements(By.CSS_SELECTOR, ".ag-header-group-cell .table-header-text")
        return [header.text.strip() for header in year_headers if header.text.strip().isdigit()]

    def _process_years(self, *year_lists):
        """
        Combine and sort year lists
        Args:
            *year_lists: Variable number of year lists to process
        Returns:
            list: Sorted list of unique years
        """
        all_years = list(set(year for sublist in year_lists for year in sublist))  # Flatten and remove duplicates
        all_years.sort()
        logger.info(f"All extracted years: {all_years}")
        return all_years

    def _extract_geo_titles(self):
        """Extract GEO titles from left column of table"""
        parent_div = self.driver.find_element(By.CSS_SELECTOR, 'div.ag-pinned-left-cols-container')
        title_elements = parent_div.find_elements(
            By.CSS_SELECTOR, 
            'span.colHeader.header-overflow.table-header-container[title]'
        )
        titles = [element.get_attribute('title') for element in title_elements]
        logger.info(f"Found {len(titles)} titles:")
        return titles

    def extract_table_data(self):
        """Main method to extract table data with retry logic"""
        if not self.driver:
            logger.error("Driver not initialized. Cannot extract data.")
            return None
        try:
            logger.info("Starting table data extraction...")
            self.driver.get(self.base_url)
            logger.info("Page loaded successfully.")            
            self.accept_cookies()
            self.wait_for_table_to_load()
            
            # Scroll to table
            logger.info("Scrolling to table...")
            table_element = self.driver.find_element(By.CSS_SELECTOR, "#estat-content-view-table")
            self._scroll_to_element(table_element)
            
            # Perform full horizontal scroll once to load all data
            scrollable_div = self.driver.find_element(By.CSS_SELECTOR, ".ag-body-horizontal-scroll-viewport")
            scroll_width = self.driver.execute_script("return arguments[0].scrollWidth", scrollable_div)
            self.driver.execute_script(f"arguments[0].scrollLeft = {scroll_width};", scrollable_div)
            time.sleep(2)
            
            # Return to start
            self.driver.execute_script("arguments[0].scrollLeft = 0;", scrollable_div)
            time.sleep(2)

            # Extract years (should all be visible now)
            all_years = self._extract_visible_years()
            print("\nTEST **All-Years**: ", all_years, "\n")

            # Extract GEO titles
            geo_titles = self._extract_geo_titles()
            print("\nTEST **Geo-Titles**: ", geo_titles, "\n")
            geo_titles_dicc_list = self._process_gdp_data(geo_titles)
            print("\nTEST **Geo-Titles-Dicc-List**: ", geo_titles_dicc_list, "\n")

            return geo_titles_dicc_list
        except Exception as e:
            logger.error(f"Error extracting table data: {e}", exc_info=True)
            return None

    def extract_complete_gdp_data(self):
        """
        Extract all GDP data with horizontal scrolling
        Returns:
            dict: Dictionary with row IDs as keys and GDP data as values
        """
        gdp_data = {}
        counter = 0
        try:
            # Perform full horizontal scroll once to load all data
            scroll_container = self.driver.find_element(
                By.CSS_SELECTOR, 
                ".ag-body-horizontal-scroll-viewport"
            )
            scroll_width = self.driver.execute_script(
                "return arguments[0].scrollWidth", 
                scroll_container
            )
            self.driver.execute_script(
                f"arguments[0].scrollLeft = {scroll_width};", 
                scroll_container
            )
            time.sleep(2)
            
            # Return to start
            self.driver.execute_script("arguments[0].scrollLeft = 0;", scroll_container)
            time.sleep(2)

            # Get all rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "div[role='row'][row-id]")            
            print("TEST **Rows**: ", len(rows))
            
            for row in rows:
                row_id = row.get_attribute('row-id')
                row_data = self.extract_row_data(row)  # Simplified method
                if row_data:  # Only add if data exists
                    gdp_data[row_id] = row_data
                    print("TEST **Row-Data**: ", row_data)
                    print(counter)
                    counter += 1              
            return gdp_data            
        except Exception as e:
            logger.error(f"Error extracting complete GDP data: {str(e)}", exc_info=True)
            return {}

    def extract_row_data(self, row):
        """
        Extract data from single row without additional scrolling
        Args:
            row: WebElement representing a table row
        Returns:
            dict: Processed row data or None if empty
        """
        row_data = {}
        try:
            cells = row.find_elements(By.CSS_SELECTOR, "div[role='gridcell'][col-id]")
            for cell in cells:
                year = cell.get_attribute('col-id')
                if year and year.isdigit():
                    value_info = self.process_cell(cell)
                    if value_info['is_available']:  # Only add if data is available
                        row_data[year] = value_info
            return row_data if row_data else None  # Return None if no data
        except Exception as e:
            logger.warning(f"Error processing row: {str(e)}")
            return None

    def process_cell(self, cell):
        """
        Process individual cell and return normalized data
        Args:
            cell: WebElement representing a table cell
        Returns:
            dict: Normalized cell data with value, flag and availability
        """
        try:
            value_element = cell.find_element(
                By.CSS_SELECTOR, 
                "span.table-cell.cell-value > span:first-child"
            )
            raw_value = value_element.text.strip()            
            return self.parse_special_value(raw_value)
        except Exception as e:
            logger.warning(f"Error processing cell: {str(e)}")
            return {'value': None, 'flag': None, 'is_available': False}

    def parse_special_value(self, raw_value):
        """
        Parse special values in cell data
        Args:
            raw_value (str): Raw text from cell
        Returns:
            dict: Processed value with flags and availability
        """
        if not raw_value or raw_value == ":":
            return {'value': None, 'flag': None, 'is_available': False}        
        flag = None
        value = raw_value
        
        # Check for special flags like (b), (p), (e)
        for special_flag in ['(b)', '(p)', '(e)']:
            if special_flag in raw_value:
                flag = special_flag[1]  # Get single letter flag
                value = raw_value.replace(special_flag, '')
                break        
        clean_value = value.strip()
        if any(c.isdigit() for c in clean_value):
            clean_value = clean_value.replace(' ', '').replace(',', '.')
        
        return {
            'value': clean_value,
            'flag': flag,
            'is_available': True
        }

    def _process_gdp_data(self, gdp_data):
        """
        Process GDP string list into dictionary list
        Args:
            gdp_data (list): List of strings in format '[CODE] Description'
        Returns:
            list: List of dictionaries in format [{'CODE': 'Description'}, ...]
        """
        gdp_data_dicc_list = []
        
        for item in gdp_data:
            # Extract code between brackets and description after
            code_start = item.find('[')
            code_end = item.find(']')
            
            if code_start != -1 and code_end != -1:
                code = item[code_start+1:code_end]
                description = item[code_end+2:].strip()
                gdp_data_dicc_list.append({code: description})
        
        return gdp_data_dicc_list
            
    def capture_screenshot(self, filename):
        """
        Capture screenshot of current page with timestamp
        Args:
            filename (str): Base filename for screenshot
        """
        if not self.driver:
            logger.error("Cannot capture screenshot: driver not initialized.")
            return            
        try:
            # Limit number of stored screenshots
            max_screenshots = 10
            screenshots = sorted(
                [f for f in os.listdir(self.screenshot_dir) if f.endswith(".png")],
                key=lambda x: os.path.getctime(os.path.join(self.screenshot_dir, x)))
            if len(screenshots) >= max_screenshots:
                oldest_screenshot = screenshots[0]
                os.remove(os.path.join(self.screenshot_dir, oldest_screenshot))
                logger.info(f"Removed oldest screenshot: {oldest_screenshot}")
            # Add timestamp to filename
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename_with_timestamp = f"{filename}_{timestamp}.png"
            filepath = os.path.join(self.screenshot_dir, filename_with_timestamp)
            self.driver.save_screenshot(filepath)
            logger.info(f"Screenshot saved as: {filepath}")
        except Exception as e:
            logger.error(f"Error capturing screenshot: {e}")