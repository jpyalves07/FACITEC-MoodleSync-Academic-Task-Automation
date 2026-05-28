"""
scraper/tasks.py
────────────────
Responsável por:
  1. Coletar links de tarefas dentro de cada matéria
  2. Entrar em cada tarefa e extrair todos os dados de envio
     (status, prazo, data de envio, arquivo, atraso)

O Moodle desta faculdade exibe os dados em uma tabela HTML
na página de cada tarefa (mod/assign/view.php).
"""

import time
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import StaleElementReferenceException

from scraper.driver import wait_for, find_all
from utils.text import clean, clean_task_title
from utils.date_parser import parse_date
from utils.logger import logger


# ── Coleta de tarefas ─────────────────────────────────────────────────────────

def get_tasks_from_course(driver: webdriver.Chrome, course: dict) -> list[dict]:
    """
    Acessa a página de uma matéria e retorna todos os links
    de tarefas (mod/assign) encontrados.

    Cada item retornado tem a estrutura:
        {"title": str, "subject": str, "url": str}
    """
    logger.info(f"  Buscando tarefas em: {course['name']}")
    tasks: list[dict] = []
    seen:  set[str]   = set()

    try:
        driver.get(course["url"])
        wait_for(driver, "#page-content, .course-content, #region-main")
        time.sleep(1.5)

        # Seletor principal — links diretos para atividades de tarefa
        for link in find_all(driver, "a[href*='/mod/assign/view.php']"):
            try:
                url   = link.get_attribute("href") or ""
                title = clean_task_title(link.text)

                if not url or url in seen:
                    continue

                # Se o link não tiver texto, tenta o elemento pai
                if not title:
                    try:
                        title = clean_task_title(
                            link.find_element(By.XPATH, "..").text
                        )
                    except Exception:
                        title = "Tarefa sem título"

                # Normaliza URL removendo parâmetros de ação
                url_base = url.split("&action=")[0]
                if url_base in seen:
                    continue

                seen.add(url_base)
                tasks.append({
                    "title":   title,
                    "subject": course["name"],
                    "url":     url_base,
                })
                logger.debug(f"    [tasks] Tarefa: {title}")

            except StaleElementReferenceException:
                continue

        # Fallback — seletor alternativo para temas diferentes do Moodle
        if not tasks:
            logger.debug("    [tasks] Seletor principal sem resultados — tentando fallback")
            for link in find_all(driver, "li.assign a.aalink, li.activity.assign a"):
                try:
                    url   = link.get_attribute("href") or ""
                    title = clean(link.text)

                    if not url or url in seen or not title:
                        continue

                    seen.add(url)
                    tasks.append({
                        "title":   title,
                        "subject": course["name"],
                        "url":     url,
                    })
                    logger.debug(f"    [tasks] Tarefa (alt): {title}")

                except StaleElementReferenceException:
                    continue

    except Exception as exc:
        logger.warning(f"  [tasks] Erro ao buscar tarefas em '{course['name']}': {exc}")

    logger.info(f"  → {len(tasks)} tarefa(s) encontrada(s) em '{course['name']}'")
    return tasks


# ── Extração de dados de uma tarefa ───────────────────────────────────────────

def extract_task_data(driver: webdriver.Chrome, task: dict) -> dict:
    """
    Acessa a página de uma tarefa e extrai todos os dados de envio.

    Retorna um dicionário com os campos:
        title, subject, link, status, submission_status, grade_status,
        deadline, deadline_iso, submission_date, submission_date_iso,
        submitted_file, late_message, is_late, last_updated
    """
    logger.info(f"    Extraindo dados: {task['title']}")

    data: dict = {
        "title":               task["title"],
        "subject":             task["subject"],
        "link":                task["url"],
        "status":              "Pendente",
        "submission_status":   "",
        "grade_status":        "",
        "deadline":            "",
        "deadline_iso":        None,
        "submission_date":     "",
        "submission_date_iso": None,
        "submitted_file":      "",
        "late_message":        "",
        "is_late":             False,
        "last_updated":        datetime.now().isoformat(),
    }

    try:
        driver.get(task["url"])
        wait_for(driver, "#page-content, #region-main, .submissionstatustable")
        time.sleep(1)

        _extract_real_title(driver, task, data)
        _extract_submission_table(driver, data)
        _extract_late_warnings(driver, data)

        data["status"] = _resolve_status(data)

        logger.debug(
            f"      Status={data['status']} | "
            f"Prazo={data['deadline_iso']} | "
            f"Atrasado={data['is_late']}"
        )

    except Exception as exc:
        logger.warning(f"    [tasks] Erro ao extrair '{task['title']}': {exc}")

    return data


# ── Helpers privados ──────────────────────────────────────────────────────────

def _extract_real_title(driver: webdriver.Chrome, task: dict, data: dict):
    """
    Extrai o título canônico da tarefa a partir do h1/h2 da página.
    O Moodle exibe títulos diferentes nas views de tarefa entregue vs pendente,
    então tentamos vários seletores em ordem de preferência.
    """
    title_found = False

    for selector in [
        "h2.page-header-headings",
        ".page-header-headings h2",
        "#region-main h2",
        ".activity-header h2",
        ".page-header h2",
        "h1.h2",
        "h2",
        "h1",
    ]:
        for element in find_all(driver, selector):
            real_title = clean(element.text)
            if real_title and len(real_title) > 2:
                data["title"] = real_title
                logger.debug(f"      Título real da página: '{real_title}'")
                title_found = True
                break
        if title_found:
            break

    # Fallback absoluto: mantém o título do card da matéria
    if not data["title"]:
        data["title"] = task["title"]
        logger.debug(f"      Título: fallback para card '{task['title']}'")


def _extract_submission_table(driver: webdriver.Chrome, data: dict):
    """
    Analisa a tabela de status de envio do Moodle e popula o dicionário `data`.

    O Moodle renderiza os dados em uma tabela <tr><th>Label</th><td>Valor</td></tr>
    ou <tr><td>Label</td><td>Valor</td></tr> dependendo do tema.
    """
    for row in find_all(driver, "table tr"):
        try:
            ths = row.find_elements(By.TAG_NAME, "th")
            tds = row.find_elements(By.TAG_NAME, "td")

            # Determina label e valor da linha
            if ths and tds:
                label = clean(ths[0].text).lower()
                value = clean(tds[0].text)
                td_element = tds[0]
            elif len(tds) >= 2:
                label = clean(tds[0].text).lower()
                value = clean(tds[1].text)
                td_element = tds[1]
            else:
                continue

            if not label or not value:
                continue

            # ── Estado do envio ───────────────────────────────────────────────
            if any(k in label for k in [
                "estado de la entrega", "estado del envío",
                "estado do envio", "submission status",
            ]):
                data["submission_status"] = value
                logger.debug(f"      submission_status = '{value}'")

            # ── Estado da nota ────────────────────────────────────────────────
            elif any(k in label for k in [
                "estado de la calificación", "estado de calificación",
                "estado da nota", "grading status",
            ]):
                data["grade_status"] = value

            # ── Tempo restante / atraso ───────────────────────────────────────
            # O Moodle desta faculdade usa "Tiempo restante" em vez da data do prazo
            elif any(k in label for k in ["tiempo restante", "time remaining"]):
                if "después" in value.lower() or "after" in value.lower():
                    data["is_late"]      = True
                    data["late_message"] = value
                    logger.debug(f"      Atraso detectado via 'Tiempo restante': '{value}'")

            # ── Prazo / Fecha límite ──────────────────────────────────────────
            elif any(k in label for k in [
                "fecha límite", "fecha de entrega",
                "prazo", "data de entrega", "due date",
            ]):
                data["deadline"] = value
                iso = parse_date(value)
                if iso:
                    data["deadline_iso"] = iso
                    logger.debug(f"      deadline_iso = '{iso}'")
                else:
                    logger.warning(f"      Prazo não parseado: '{value}'")

            # ── Data da última modificação / envio ────────────────────────────
            elif any(k in label for k in [
                "última modificación", "última modificacion",
                "última modificação", "last modified",
                "fecha de envío", "fecha envío",
            ]):
                data["submission_date"] = value
                iso = parse_date(value)
                if iso:
                    data["submission_date_iso"] = iso

            # ── Arquivo(s) entregue(s) ────────────────────────────────────────
            # A célula frequentemente contém "nome_arquivo\ndata_envio"
            elif any(k in label for k in [
                "archivos entregados", "archivo entregado",
                "arquivo enviado", "file submissions",
            ]):
                lines = [ln.strip() for ln in value.split("\n") if ln.strip()]
                if lines:
                    data["submitted_file"] = lines[0]

                    # Segunda linha geralmente é a data de envio do arquivo
                    if len(lines) >= 2 and not data["submission_date"]:
                        data["submission_date"] = lines[1]
                        iso = parse_date(lines[1])
                        if iso and not data["submission_date_iso"]:
                            data["submission_date_iso"] = iso

                # Tenta capturar o href real do arquivo (URL de download)
                try:
                    file_links = td_element.find_elements(By.TAG_NAME, "a")
                    if file_links:
                        href = file_links[0].get_attribute("href") or ""
                        if href:
                            data["submitted_file"] = href
                except Exception:
                    pass

        except StaleElementReferenceException:
            continue
        except Exception:
            continue


def _extract_late_warnings(driver: webdriver.Chrome, data: dict):
    """
    Verifica elementos de aviso de atraso presentes no corpo da página
    (alertas, banners de prazo vencido).
    """
    warning_selectors = [
        ".alert-danger",
        ".alert.alert-error",
        ".latesubmission",
        ".overduewarning",
        ".alert-warning",
    ]
    late_keywords = ["tarde", "atraso", "después", "atrasad", "after"]

    for selector in warning_selectors:
        for element in find_all(driver, selector):
            text = clean(element.text)
            if text and any(kw in text.lower() for kw in late_keywords):
                data["late_message"] = text
                data["is_late"]      = True
                return  # Primeiro aviso encontrado é suficiente


def _resolve_status(data: dict) -> str:
    """
    Determina o status final da tarefa com base nos campos extraídos.

    Prioridade:
        1. submission_status (texto retornado pelo Moodle)
        2. submitted_file    (arquivo presente = entregue)
        3. Padrão: "Pendente"
    """
    sub = (data.get("submission_status") or "").lower()

    keywords_entregue = [
        "enviado para calificar", "entregado para calificar",
        "submitted for grading", "enviado", "entregado", "entregue",
    ]
    keywords_pendente = [
        "todavía no se han realizado envíos", "no se han realizado envíos",
        "sin envío", "não enviado", "not submitted", "pendente",
    ]

    for keyword in keywords_entregue:
        if keyword in sub:
            return "Atrasado" if data.get("is_late") else "Entregue"

    for keyword in keywords_pendente:
        if keyword in sub:
            return "Pendente"

    # Se há arquivo mas o status não foi reconhecido
    if data.get("submitted_file"):
        return "Atrasado" if data.get("is_late") else "Entregue"

    return "Pendente"
