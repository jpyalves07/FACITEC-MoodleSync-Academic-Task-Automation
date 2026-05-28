"""
notion/client.py
────────────────
Camada de integração com a API REST do Notion.
Responsável por criar, atualizar e buscar páginas no banco de dados.

Documentação da API: https://developers.notion.com/reference
"""

from datetime import datetime
from typing import Optional

import requests

from config.settings import NOTION_TOKEN, NOTION_DB_ID, NOTION_API, NOTION_VER
from utils.logger import logger


# ── Cabeçalhos HTTP ───────────────────────────────────────────────────────────

def _headers() -> dict:
    return {
        "Authorization":  f"Bearer {NOTION_TOKEN}",
        "Content-Type":   "application/json",
        "Notion-Version": NOTION_VER,
    }


# ── Busca de página ───────────────────────────────────────────────────────────

def find_page(title: str, subject: str) -> Optional[str]:
    """
    Busca uma página existente no banco de dados do Notion.

    Estratégia em dois estágios para máxima compatibilidade:
      1. Filtra por Nome (título) + Matéria (rich_text)
      2. Fallback: filtra apenas por Nome (caso o tipo da coluna Matéria seja diferente)

    Retorna o ID da página encontrada, ou None.
    """
    # Estágio 1: filtro combinado
    payload = {
        "filter": {
            "and": [
                {"property": "Nome",    "title":     {"equals": title}},
                {"property": "Matéria", "rich_text": {"equals": subject}},
            ]
        }
    }
    page_id = _query_database(payload)
    if page_id:
        logger.debug(f"      [notion] Página encontrada por Nome+Matéria → {page_id}")
        return page_id

    # Estágio 2: apenas pelo título
    payload_fallback = {
        "filter": {"property": "Nome", "title": {"equals": title}}
    }
    page_id = _query_database(payload_fallback)
    if page_id:
        logger.debug(f"      [notion] Página encontrada por Nome (fallback) → {page_id}")
        return page_id

    logger.debug(f"      [notion] Nenhuma página encontrada para '{title}'")
    return None


def _query_database(payload: dict) -> Optional[str]:
    """Executa uma query no banco e retorna o ID do primeiro resultado."""
    try:
        response = requests.post(
            f"{NOTION_API}/databases/{NOTION_DB_ID}/query",
            headers=_headers(),
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        results = response.json().get("results", [])
        return results[0]["id"] if results else None
    except Exception as exc:
        logger.warning(f"[notion] Erro ao consultar banco: {exc}")
        return None


# ── Criação e atualização ─────────────────────────────────────────────────────

def create_page(data: dict) -> bool:
    """
    Cria uma nova página no banco de dados do Notion com os dados da tarefa.
    Retorna True em caso de sucesso.
    """
    try:
        payload = _build_payload(data)
        payload["parent"] = {"database_id": NOTION_DB_ID}

        response = requests.post(
            f"{NOTION_API}/pages",
            headers=_headers(),
            json=payload,
            timeout=15,
        )

        if not response.ok:
            logger.error(
                f"  [notion] ❌ Erro ao criar '{data['title']}' "
                f"(HTTP {response.status_code}): {response.text[:500]}"
            )
            return False

        logger.info(f"  [notion] ✅ Criado: {data['title']}")
        return True

    except Exception as exc:
        logger.error(f"  [notion] ❌ Erro ao criar '{data['title']}': {exc}")
        return False


def update_page(page_id: str, data: dict) -> bool:
    """
    Atualiza uma página existente no Notion com os dados mais recentes da tarefa.
    Retorna True em caso de sucesso.
    """
    try:
        payload = _build_payload(data)

        response = requests.patch(
            f"{NOTION_API}/pages/{page_id}",
            headers=_headers(),
            json=payload,
            timeout=15,
        )

        if not response.ok:
            logger.error(
                f"  [notion] ❌ Erro ao atualizar '{data['title']}' "
                f"(HTTP {response.status_code}): {response.text[:500]}"
            )
            return False

        logger.info(f"  [notion] 🔄 Atualizado: {data['title']}")
        return True

    except Exception as exc:
        logger.error(f"  [notion] ❌ Erro ao atualizar '{data['title']}': {exc}")
        return False


def sync_page(data: dict) -> bool:
    """
    Decide automaticamente entre criar ou atualizar uma página no Notion.
    Garante que o título nunca seja vazio (usa a URL como fallback).
    """
    title   = (data.get("title") or "").strip()
    subject = data.get("subject", "")

    if not title:
        title = data.get("link", "tarefa-sem-titulo")
        data["title"] = title
        logger.warning(f"  [notion] ⚠️  Título vazio — usando fallback: '{title}'")

    page_id = find_page(title, subject)

    if page_id:
        return update_page(page_id, data)
    else:
        return create_page(data)


# ── Construção do payload ─────────────────────────────────────────────────────

def _build_payload(data: dict) -> dict:
    """
    Monta o payload JSON com as propriedades do banco de dados do Notion.

    Mapeamento de tipos:
        Nome              → title
        Matéria           → rich_text
        Status            → select
        Status Envio      → rich_text
        Status Nota       → rich_text
        Prazo             → date  (ISO 8601)
        Data Envio        → rich_text  (coluna configurada como Text no Notion)
        Atraso            → rich_text
        Arquivo           → url (se link) ou rich_text (se nome de arquivo)
        Link              → url
        Última Atualização→ date  (ISO 8601 com horário)
    """
    def txt(value) -> dict:
        """Formata um valor como propriedade rich_text do Notion."""
        return {
            "rich_text": [{"text": {"content": str(value or "")[:2000]}}]
        }

    def date_prop(iso: Optional[str]) -> dict:
        """Formata uma string ISO 8601 como propriedade date do Notion."""
        return {"date": {"start": iso}} if iso else {"date": None}

    # Data de envio: coluna no Notion é Text (rich_text), não Date
    sub_date = data.get("submission_date_iso") or data.get("submission_date", "")

    # Arquivo: se for URL completa, usa tipo url; caso contrário, rich_text
    arquivo = data.get("submitted_file", "")
    arquivo_prop = (
        {"url": arquivo}
        if arquivo.startswith("http")
        else txt(arquivo)
    )

    return {
        "properties": {
            "Nome":               {"title": [{"text": {"content": data.get("title", "")[:2000]}}]},
            "Matéria":            txt(data.get("subject", "")),
            "Status":             {"select": {"name": data.get("status", "Pendente")}},
            "Status Envio":       txt(data.get("submission_status", "")),
            "Status Nota":        txt(data.get("grade_status", "")),
            "Prazo":              date_prop(data.get("deadline_iso")),
            "Data Envio":         txt(sub_date),
            "Atraso":             txt(data.get("late_message", "")),
            "Arquivo":            arquivo_prop,
            "Link":               {"url": data.get("link") or None},
            "Última Atualização": date_prop(datetime.now().strftime("%Y-%m-%dT%H:%M:%S")),
        }
    }
