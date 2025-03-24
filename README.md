🌐 Py-Web-Scraping-03

<img alt="GPLv3 License" src="https://img.shields.io/badge/License-GPLv3-blue.svg">

<img alt="Python Version" src="https://img.shields.io/badge/Python->=3.13-blue">

<img alt="Selenium Version" src="https://img.shields.io/badge/Selenium->=4.29.0-green">

<img alt="Django Version" src="https://img.shields.io/badge/Django->=5.1.7-darkgreen">
📖 Descripción del Proyecto
Py-Web-Scraping-03 es un proyecto diseñado para realizar scraping de datos desde la web de Eurostat, una plataforma que proporciona estadísticas y datos económicos de la Unión Europea. Este proyecto utiliza herramientas avanzadas como Selenium, BeautifulSoup, y Pandas para automatizar la extracción, procesamiento y análisis de datos. Además, los datos extraídos pueden ser exportados a formatos como Excel para su posterior análisis.

El proyecto también incluye una integración con Django, lo que permite gestionar los datos extraídos a través de una interfaz web.

🚀 Características Principales
Automatización del scraping: Uso de Selenium para interactuar con tablas dinámicas y contenido renderizado por JavaScript.
Procesamiento de datos: Limpieza y análisis de datos con Pandas.
Exportación: Generación de archivos Excel con los datos extraídos utilizando OpenPyXL.
Interfaz web: Gestión de los datos extraídos a través de un backend basado en Django.
Compatibilidad: Diseñado para Python 3.13 o superior.

py-web-scraping-03/
├── scraper/
│   ├── eurostat_scraper.py       # Código principal para el scraping
│   ├── utils.py                  # Funciones auxiliares
│   └── tests/                    # Pruebas unitarias
├── manage.py                     # Script de Django para gestionar el proyecto
├── requirements.txt              # Dependencias del proyecto
├── pyproject.toml                # Configuración del proyecto
├── README.md                     # Documentación del proyecto
├── screenshots/                  # Capturas de pantalla generadas durante el scraping
└── logs/                         # Archivos de log para depuración



🛠️ Requisitos Previos
Antes de comenzar, asegúrate de tener instalados los siguientes componentes:

Python 3.13 o superior
Google Chrome (o Firefox si usas Geckodriver)
ChromeDriver o GeckoDriver (administrado automáticamente por webdriver-manager)

🛠️ Instalación en Linux/MacOS
Opción 1: Usando pip

1.Crear un entorno virtual:
python3 -m venv venv
source venv/bin/activate

2.Instalar las dependencias:
pip install -r requirements.txt

3.Verificar la instalación:
python --version
pip list

----
Opción 2: Usando uv (alias de pipenv)

1.Instalar pipenv (si no lo tienes instalado):
pip install pipenv

2.Crear el entorno virtual e instalar dependencias:
uv install

3.Sincronizar dependencias:
uv sync

4.Activar el entorno virtual:
uv shell

5.Verificar la instalación:
python --version
uv graph

----

🛠️ Instalación en Windows

Opción 1: Usando pip

1.Crear un entorno virtual:
python -m venv venv
venv\Scripts\activate

2.Instalar las dependencias:
pip install -r requirements.txt

3.Verificar la instalación:
python --version
pip list

----

Opción 2: Usando uv (alias de pipenv)

1.Instalar pipenv (si no lo tienes instalado):
pip install pipenv

2.Crear el entorno virtual e instalar dependencias:
uv install

3.Sincronizar dependencias:
uv sync

4.Activar el entorno virtual:
uv shell

5.Verificar la instalación:
python --version
uv graph

----

⚠️ Nota Importante

- uv install: Instala las dependencias especificadas en pyproject.toml y genera un archivo Pipfile.lock.

- uv sync: Asegura que las dependencias instaladas en el entorno virtual coincidan exactamente con las especificadas en el archivo Pipfile.lock.

- No ejecutes ambos métodos (pip y uv) al mismo tiempo. Elige uno de los dos.

