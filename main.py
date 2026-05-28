"""
main.py
───────
Ponto de entrada e orquestrador principal da aplicação.

Uso:
    python main.py              # executa uma sincronização
    python main.py --loop       # executa em loop contínuo (cron próprio)
    python main.py --diag       # diagnóstico: lista matérias e links encontrados
"""

import sys
import time
from datetime import datetime

from selenium.common.exceptions import WebDriverException

from config.settings import LOOP_INTERVAL
from scraper.driver import create_driver
from scraper.auth import login
from scraper.courses import get_courses
from scraper.tasks import get_tasks_from_course, extract_task_data
from notion.client import sync_page
from utils.logger import logger


# ── Sincronização principal ───────────────────────────────────────────────────

def run_sync() -> dict:
    """
    Executa um ciclo completo de sincronização:
      1. Abre o navegador e faz login no Moodle
      2. Coleta todas as matérias do aluno
      3. Para cada matéria, coleta e extrai dados de todas as tarefas
      4. Sincroniza cada tarefa com o banco de dados do Notion

    Retorna um dicionário com estatísticas da execução.
    """
    start  = datetime.now()
    stats  = {"courses": 0, "tasks": 0, "success": 0, "errors": 0}
    driver = None

    logger.info("=" * 60)
    logger.info(f"  MOODLE → NOTION SYNC  |  {start.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)

    try:
        driver = create_driver()

        if not login(driver):
            logger.error("Abortando: falha na autenticação.")
            return stats

        courses = get_courses(driver)
        stats["courses"] = len(courses)

        if not courses:
            logger.warning("Nenhuma matéria encontrada. Encerrando.")
            return stats

        for course in courses:
            tasks = get_tasks_from_course(driver, course)

            for task in tasks:
                stats["tasks"] += 1
                try:
                    task_data = extract_task_data(driver, task)
                    success   = sync_page(task_data)

                    if success:
                        stats["success"] += 1
                    else:
                        stats["errors"] += 1

                    time.sleep(0.5)  # Evita rate-limit da API do Notion

                except Exception as exc:
                    logger.error(f"  Erro inesperado em '{task.get('title')}': {exc}")
                    stats["errors"] += 1

    except KeyboardInterrupt:
        logger.info("Execução interrompida pelo usuário.")

    except WebDriverException as exc:
        logger.exception(f"Erro crítico do WebDriver: {exc}")

    finally:
        if driver:
            driver.quit()
            logger.debug("WebDriver encerrado.")

    elapsed = (datetime.now() - start).seconds
    logger.info("=" * 60)
    logger.info(
        f"  Concluído em {elapsed}s  |  "
        f"Matérias: {stats['courses']}  |  "
        f"Tarefas: {stats['tasks']}  |  "
        f"✅ {stats['success']}  |  ❌ {stats['errors']}"
    )
    logger.info("=" * 60)

    return stats


# ── Modo loop ─────────────────────────────────────────────────────────────────

def run_loop():
    """
    Executa sincronizações em loop contínuo com intervalo configurável via .env
    (variável LOOP_INTERVAL, padrão: 3600 segundos).
    """
    interval_min = LOOP_INTERVAL // 60
    logger.info(f"Modo loop ativo. Intervalo: {interval_min} minuto(s).")

    while True:
        try:
            run_sync()
        except Exception as exc:
            logger.exception(f"Erro no loop: {exc}")

        logger.info(f"Próxima execução em {interval_min} minuto(s)...")
        time.sleep(LOOP_INTERVAL)


# ── Diagnóstico ───────────────────────────────────────────────────────────────

def run_diagnostic():
    """
    Modo diagnóstico: lista matérias e tarefas encontradas sem sincronizar.
    Salva o HTML da primeira matéria em logs/pagina_curso.html para inspeção.
    """
    import os
    from selenium.webdriver.common.by import By

    driver = create_driver()

    if not login(driver):
        print("❌ Falha na autenticação.")
        driver.quit()
        return

    courses = get_courses(driver)
    if not courses:
        print("❌ Nenhuma matéria encontrada.")
        driver.quit()
        return

    print(f"\n✅ {len(courses)} matéria(s) encontrada(s):\n")
    for c in courses:
        print(f"  • {c['name']}")
        print(f"    {c['url']}")

    # Inspeciona a primeira matéria
    course = courses[0]
    print(f"\n🔍 Inspecionando: {course['name']}")
    driver.get(course["url"])
    time.sleep(3)

    # Salva HTML para análise manual
    os.makedirs("logs", exist_ok=True)
    with open("logs/pagina_curso.html", "w", encoding="utf-8") as f:
        f.write(driver.page_source)
    print("  HTML salvo em logs/pagina_curso.html")

    # Lista tarefas encontradas
    tasks = get_tasks_from_course(driver, course)
    print(f"\n  📋 {len(tasks)} tarefa(s):\n")
    for t in tasks:
        print(f"    • {t['title']}")
        print(f"      {t['url']}")

    driver.quit()
    print("\n✅ Diagnóstico concluído.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if "--loop" in sys.argv:
        run_loop()
    elif "--diag" in sys.argv:
        run_diagnostic()
    else:
        result = run_sync()
        sys.exit(0 if result["errors"] == 0 else 1)
