"""
config/settings.py
──────────────────
Centraliza todas as configurações da aplicação.
Os valores são lidos de variáveis de ambiente (arquivo .env).
"""

import os
from dotenv import load_dotenv

# Carrega o .env da raiz do projeto
load_dotenv()


# ── Moodle ────────────────────────────────────────────────────────────────────

MOODLE_BASE_URL  = os.getenv("MOODLE_BASE_URL", "https://campusvirtual.facitec.edu.py")
MOODLE_USER      = os.getenv("MOODLE_USER", "")
MOODLE_PASS      = os.getenv("MOODLE_PASS", "")

MOODLE_LOGIN_URL  = f"{MOODLE_BASE_URL}/login/index.php"
MOODLE_COURSES_URL = f"{MOODLE_BASE_URL}/my/courses.php"


# ── Notion ────────────────────────────────────────────────────────────────────

NOTION_TOKEN  = os.getenv("NOTION_TOKEN", "")
NOTION_DB_ID  = os.getenv("NOTION_DB_ID", "")
NOTION_API    = "https://api.notion.com/v1"
NOTION_VER    = "2022-06-28"


# ── WebDriver ─────────────────────────────────────────────────────────────────

HEADLESS       = os.getenv("HEADLESS", "true").lower() == "true"
WAIT_TIMEOUT   = int(os.getenv("WAIT_TIMEOUT", "20"))
PAGE_LOAD_TIMEOUT = int(os.getenv("PAGE_LOAD_TIMEOUT", "30"))


# ── App ───────────────────────────────────────────────────────────────────────

DEBUG          = os.getenv("DEBUG", "false").lower() == "true"
LOOP_INTERVAL  = int(os.getenv("LOOP_INTERVAL", "3600"))   # segundos entre execuções
LOG_FILE       = os.getenv("LOG_FILE", "logs/moodle_sync.log")
