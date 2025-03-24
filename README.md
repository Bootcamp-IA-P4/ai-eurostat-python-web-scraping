
# 🌐 Django Eurostat Web-Scraping

![GPLv3 License](https://img.shields.io/badge/License-GPLv3-blue.svg)
![Python Version](https://img.shields.io/badge/Python->=3.13-blue)
![Selenium Version](https://img.shields.io/badge/Selenium->=4.29.0-green)
![Django Version](https://img.shields.io/badge/Django->=5.1.7-darkgreen)
![UV](https://img.shields.io/badge/UV-1.0+-lightgrey)

## 📖 Descripción del Proyecto

Py-Web-Scraping-03 es un sistema avanzado para extracción automatizada de datos estadísticos de [Eurostat](https://ec.europa.eu/eurostat), con capacidades de:

- **Web scraping** de tablas dinámicas con JavaScript
- **Procesamiento ETL** (Extracción, Transformación, Carga)
- **Visualización** mediante interfaz web Django
- **Exportación** a múltiples formatos (Excel, CSV, JSON)

🔍 **Tecnologías clave implementadas**:
```python
# Stack tecnológico completo
tech_stack = {
    "scraping": ["Selenium", "BeautifulSoup", "Pandas"],
    "backend": ["Django"],
    "data": ["Pandas", "OpenPyXL", "NumPy"],
    "tools": ["UV", "WebDriver Manager"],
}
```

## 🚀 Características Principales

### 🔧 **Módulo de Scraping Avanzado**
```python
from selenium.webdriver import ChromeOptions
from bs4 import BeautifulSoup

# Configuración profesional discutida
options = ChromeOptions()
options.add_argument("--headless=new")  # Modo sin interfaz gráfica
options.add_argument("--disable-blink-features=AutomationControlled")
```

### 📊 **Procesamiento de Datos**
- Limpieza automática de valores especiales (`(b)`, `(e)`, `(p)`)
- Normalización de formatos numéricos europeos (`1.234,56` → `1234.56`)
- Identificación automática de metadatos (EU vs Eurozone)

### 🌐 **Interfaz Django**
```bash
# Estructura MVC implementada
django-admin startproject eurostat_scraper
├── core/
│   ├── models.py       # Modelos GeoArea y GDPData
│   ├── admin.py        # Configuración avanzada del Admin
│   └── management/     # Comandos personalizados
```

---

## 🛠️ Requisitos Previos

| Componente       | Versión Mínima | Notas                          |
|------------------|----------------|--------------------------------|
| Python           | 3.13+          | Requiere soporte para type hints |
| Chrome/Firefox   | Latest         | Para ejecución del navegador    |
| UV               | 1.0+           | Alternativa moderna a pip       |

---

## ⚙️ Instalación

### Linux/macOS (Recomendado con UV)
```bash
# 1. Crear entorno virtual
python -m venv .venv && source .venv/bin/activate

# 2. Instalar UV (si no está instalado)
pip install uv

# 3. Instalar dependencias (desde pyproject.toml)
uv pip install -e .

# 4. Verificar
uv pip list
```

### Windows (PowerShell)
```powershell
# 1. Entorno virtual
py -m venv .venv; .venv\Scripts\activate

# 2. Instalar con UV
pip install uv
uv pip sync
```

### 🧪 Modo Desarrollo
```bash
# Instalar dependencias + herramientas de testing
uv pip install -e ".[dev]"

# Ejecutar tests (como discutimos)
pytest scraper/tests/ -v
```

---

## 🏗️ Estructura del Proyecto

```bash
py-web-scraping-03/
├── scraper/
│   ├── eurostat_scraper.py       # Lógica principal de scraping
│   ├── utils.py                  # Funciones de limpieza de datos
│   └── tests/                    # Pruebas con mocks de Selenium
├── config/
│   ├── settings.py               # Django settings modularizados
│   └── asgi.py                   
├── logs/                         # Logs automatizados (RotatingFileHandler)
└── screenshots/                  # Capturas de fallos (como vimos)
```

---

## 💡 Uso Avanzado

### Ejemplo de Scraping con Retries
```python
from scraper.eurostat_scraper import EurostatScraper

with EurostatScraper(headless=True) as scraper:
    data = scraper.extract_complete_gdp_data()
    scraper.export_to_excel(data, "eurostat_data.xlsx")
```

### Comandos Django Personalizados
```bash
python manage.py import_eurostat_data \
    --years 2020-2023 \
    --countries "ES,FR,DE"
```

---

## 📌 Mejoras Implementadas:

1. **Manejo profesional de tablas dinámicas**:
   - Scroll horizontal automatizado
   - Detección de datos lazy-loaded

2. **Sistema de logging mejorado**:
   ```python
   # Configuración que desarrollamos
   logger.addHandler(RotatingFileHandler(
       "logs/scraper.log", 
       maxBytes=5*1024*1024, 
       backupCount=3
   ))
   ```

3. **Configuración avanzada de Selenium**:
   - Desactivación de imágenes para mejor rendimiento
   - Timeouts configurables por selector

---

## 📄 Licencia

Este proyecto está bajo licencia [GPLv3](https://www.gnu.org/licenses/gpl-3.0.html). Consulte el archivo `LICENSE` para más detalles.

---

> 💡 **Tip**: usa `uv pip compile --upgrade` para actualizar dependencias de forma segura y `uv pip sync` para replicar entornos exactos.

---

## Capturas del Proceso

### 1. Configuración Inicial del Proyecto
![Configuración](docs/images/initial_conf.png)
*Figura 1: Establecimiento de tareas iniciales y milestones en el tablero de proyecto*

### 2. Investigación de Tecnologías
![Investigación Tecnologías](docs/images/initial_researching.png)  
*Figura 2: Búsqueda de tecnologías adecuadas para web scraping (BeautifulSoup, Scrapy, Selenium)*

### 3. Estructura de Ramas Git
![Ramas Git](docs/images/branches_structure.png)  
*Figura 3: Estructura de ramas con `main`, `develop` y `feature/` para desarrollo*

### 4. Progreso del Desarrollo
![Progreso](./docs/images/spint_2.png)  
*Figura 4: Estado actual de las tareas en el sprint (2/5 completadas)*

### 5. Estructura de Datos Eurostat
![Estructura Eurostat](./docs/images/eurostat_data_structure.png)  
*Figura 5: Jerarquía de datasets de GDP en Eurostat (ESA 2010 framework)*

### 6. Vista de Tabla de Datos
![Tabla Datos](./docs/images/table_data.png)  
*Figura 6: Vista preliminar de los datos GDP por país/región*

### 7. Datos Numéricos Detallados
![Datos Numéricos](./docs/images/detail_numeric_data.png)  
*Figura 7: Valores específicos de GDP con flags de calidad de datos*

### 8. Tabla Completa de Resultados
![Tabla Completa](./docs/images/Captura_desde_2025-03-19_21-00-04.png)  
*Figura 8: Dataset final con valores GDP (en millones) y metadatos*

## Notas Técnicas

1. **Flags de Datos**:  
   - `(b)`: Break in time series (cambio metodológico)  
   - `(p)`: Provisional (datos preliminares)  
   - `(e)`: Estimated (estimación)  
   - `:`: Not available (no disponible)

2. **Estructura de Datos**:  
   Los datos siguen el estándar ESA 2010 de cuentas nacionales, con desglose por:
   - Componentes principales (output, expenditure, income)
   - Industrias (NACE Rev.2)
   - Áreas geográficas (EU, Euro area, países individuales)

