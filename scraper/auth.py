"""
scraper/auth.py
───────────────
Responsável exclusivamente pelo processo de autenticação no Moodle.
Preenche o formulário de login e valida o redirecionamento pós-login.
"""

import time

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from config.settings import MOODLE_LOGIN_URL, MOODLE_USER, MOODLE_PASS, WAIT_TIMEOUT
from utils.logger import logger


def login(driver: webdriver.Chrome) -> bool:
    """
    Realiza o login no Moodle.

    Retorna:
        True  — login bem-sucedido
        False — credenciais inválidas ou erro inesperado
    """
    logger.info("Iniciando autenticação no Moodle...")

    if not MOODLE_USER or not MOODLE_PASS:
        logger.error(
            "Credenciais não configuradas. "
            "Defina MOODLE_USER e MOODLE_PASS no arquivo .env"
        )
        return False

    try:
        driver.get(MOODLE_LOGIN_URL)

        # Aguarda o campo de usuário estar disponível
        WebDriverWait(driver, WAIT_TIMEOUT).until(
            EC.presence_of_element_located((By.ID, "username"))
        )
        time.sleep(1.5)  # Pausa para evitar detecção de bot

        # Preenche o formulário
        username_field = driver.find_element(By.ID, "username")
        password_field = driver.find_element(By.ID, "password")

        username_field.clear()
        username_field.send_keys(MOODLE_USER)

        password_field.clear()
        password_field.send_keys(MOODLE_PASS)

        driver.find_element(By.ID, "loginbtn").click()
        time.sleep(3)

        # Valida: se ainda estiver na página de login, as credenciais são inválidas
        if "login/index.php" in driver.current_url:
            logger.error(
                "Falha na autenticação. Verifique MOODLE_USER e MOODLE_PASS no .env"
            )
            return False

        logger.info(f"Autenticação bem-sucedida. Redirecionado para: {driver.current_url}")
        return True

    except Exception as exc:
        logger.exception(f"Erro inesperado durante o login: {exc}")
        return False
