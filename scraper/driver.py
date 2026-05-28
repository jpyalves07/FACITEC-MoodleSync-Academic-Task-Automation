"""
scraper/driver.py
─────────────────
Fábrica do WebDriver Chrome com configurações anti-detecção.
Centraliza a criação e teardown do driver Selenium.

Importante:
  O Chrome (navegador) deve estar instalado no computador do usuário.
  O ChromeDriver (ponte entre Python e Chrome) é baixado automaticamente
  pelo webdriver-manager apenas se necessário — é um arquivo pequeno (~10 MB)
  e compatível com a versão do Chrome já instalada.
"""

import os
import shutil
import platform

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager

from config.settings import HEADLESS, WAIT_TIMEOUT, PAGE_LOAD_TIMEOUT
from utils.logger import logger


# Caminhos padrão do Chrome por sistema operacional
_CHROME_PATHS = {
    "Windows": [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
    ],
    "Darwin": [  # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
    ],
    "Linux": [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/bin/brave-browser",
    ],
}


def _find_chrome_binary() -> str | None:
    """
    Localiza o executável do Chrome (ou Brave/Edge compatível) instalado no sistema.
    Tenta primeiro os caminhos conhecidos, depois busca no PATH do sistema.
    Retorna o caminho encontrado ou None.
    """
    system = platform.system()

    for path in _CHROME_PATHS.get(system, []):
        if os.path.exists(path):
            logger.debug(f"[driver] Chrome encontrado em: {path}")
            return path

    # Fallback: busca no PATH do sistema operacional
    for name in ("google-chrome", "google-chrome-stable", "chromium",
                  "chromium-browser", "brave-browser", "msedge"):
        found = shutil.which(name)
        if found:
            logger.debug(f"[driver] Chrome encontrado no PATH: {found}")
            return found

    return None


def create_driver() -> webdriver.Chrome:
    """
    Inicializa e retorna um WebDriver Chrome configurado para:
      - usar o Chrome JA instalado no sistema do usuario (nao baixa o Chrome)
      - baixar apenas o ChromeDriver compativel (arquivo ~10 MB, so na 1a execucao)
      - modo headless opcional (via .env)
      - bypass de deteccao de automacao
    """
    opts = Options()

    # Aponta para o Chrome instalado no sistema — nao baixa o navegador
    chrome_binary = _find_chrome_binary()
    if chrome_binary:
        opts.binary_location = chrome_binary
        logger.debug(f"[driver] Usando Chrome instalado em: {chrome_binary}")
    else:
        logger.warning(
            "[driver] Chrome nao encontrado nos caminhos padrao. "
            "Certifique-se de ter o Google Chrome instalado: https://www.google.com/chrome"
        )

    if HEADLESS:
        opts.add_argument("--headless=new")

    # Estabilidade em ambientes sem GPU/sandbox
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")

    # Anti-deteccao de automacao
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)

    # Configuracoes gerais
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--lang=es,pt-BR;q=0.9")

    # ChromeDriverManager baixa APENAS o driver (nao o Chrome)
    # e guarda em cache local — so baixa uma vez por versao
    service = Service(ChromeDriverManager().install())

    driver = webdriver.Chrome(service=service, options=opts)
    driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

    # Remove a propriedade webdriver do navigator para evitar deteccao
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    logger.debug("WebDriver Chrome iniciado com sucesso.")
    return driver


def wait_for(driver: webdriver.Chrome, css: str, timeout: int = WAIT_TIMEOUT):
    """
    Aguarda ate que um elemento CSS esteja presente na pagina.
    Retorna o elemento ou None se o timeout for atingido.
    """
    try:
        return WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, css))
        )
    except TimeoutException:
        logger.debug(f"[driver] Timeout aguardando seletor: '{css}'")
        return None


def find_all(driver: webdriver.Chrome, css: str) -> list:
    """
    Retorna todos os elementos que correspondem ao seletor CSS.
    Retorna lista vazia em caso de erro (sem propagar excecao).
    """
    try:
        return driver.find_elements(By.CSS_SELECTOR, css)
    except Exception:
        return []
