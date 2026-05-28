"""
scraper/courses.py
──────────────────
Responsável por coletar a lista de matérias (cursos) do aluno
a partir da página /my/courses.php do Moodle.

Estratégia em dois estágios:
  1. Busca por seletores CSS conhecidos do Moodle
  2. Fallback via extração do objeto JavaScript window.local_mail_navbar_data
"""

import time

from selenium import webdriver
from selenium.common.exceptions import StaleElementReferenceException

from config.settings import MOODLE_COURSES_URL, MOODLE_BASE_URL
from scraper.driver import wait_for, find_all
from utils.text import clean
from utils.logger import logger


# Seletores CSS conhecidos nas diferentes versões e temas do Moodle
_COURSE_SELECTORS = [
    "a[href*='/course/view.php']",
    ".coursename a",
    ".course-info-container a",
    "[data-region='course-content'] a",
    ".card-title a",
    "h3.coursename a",
    "h4.coursename a",
    ".multiline a",
    ".coursebox a.aalink",
    "a.aalink[href*='course']",
]


def get_courses(driver: webdriver.Chrome) -> list[dict]:
    """
    Retorna a lista de matérias do aluno autenticado.

    Cada item tem a estrutura:
        {"name": str, "url": str}
    """
    logger.info("Coletando matérias em /my/courses.php ...")
    driver.get(MOODLE_COURSES_URL)
    time.sleep(3)

    courses: list[dict] = []
    seen: set[str] = set()

    # Estágio 1: seletores CSS
    for selector in _COURSE_SELECTORS:
        links = find_all(driver, selector)
        if links:
            logger.debug(f"  [courses] Seletor '{selector}' → {len(links)} link(s)")

        for link in links:
            try:
                url  = link.get_attribute("href") or ""
                name = clean(link.text)

                if not url or not name or len(name) < 3:
                    continue
                if "/course/view.php" not in url and "/course/" not in url:
                    continue
                if url in seen:
                    continue

                seen.add(url)
                courses.append({"name": name, "url": url})
                logger.debug(f"  [courses] Matéria: {name}")

            except StaleElementReferenceException:
                continue

    # Estágio 2: fallback via JSON embutido no HTML
    if not courses:
        logger.info("  [courses] Nenhum curso por CSS — tentando extração via JS...")
        courses = _extract_from_js(driver, seen)

    logger.info(f"Total de matérias encontradas: {len(courses)}")
    return courses


def _extract_from_js(driver: webdriver.Chrome, seen: set) -> list[dict]:
    """
    Extrai cursos do objeto JavaScript window.local_mail_navbar_data,
    disponível em algumas instalações do Moodle com o plugin local_mail.
    """
    courses: list[dict] = []
    try:
        result = driver.execute_script("""
            try {
                var data = window.local_mail_navbar_data;
                if (data && data.courses) {
                    return data.courses.map(function(c) {
                        return {id: c.id, name: c.fullname};
                    });
                }
            } catch(e) {}
            return [];
        """)

        if result:
            for item in result:
                course_id = item.get("id")
                name      = (item.get("name") or "").strip()
                url       = f"{MOODLE_BASE_URL}/course/view.php?id={course_id}"

                if name and url not in seen:
                    seen.add(url)
                    courses.append({"name": name, "url": url})
                    logger.debug(f"  [courses] Matéria (JS): {name}")

    except Exception as exc:
        logger.warning(f"  [courses] Falha na extração via JS: {exc}")

    return courses
