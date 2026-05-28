"""
utils/date_parser.py
────────────────────
Funções para converter datas em espanhol e português
(formato Moodle) para strings ISO 8601.

Exemplos de entrada suportados:
  - "viernes, 6 de marzo de 2026, 21:30"
  - "27 de marzo de 2026, 20:54"
  - "6 de março de 2026 às 21:30"
"""

import re
from typing import Optional

from utils.logger import logger


# Mapeamento de nomes de meses (espanhol e português) → número
_MESES: dict[str, str] = {
    # Espanhol
    "enero": "01", "febrero": "02", "marzo": "03",
    "abril": "04", "mayo": "05", "junio": "06",
    "julio": "07", "agosto": "08", "septiembre": "09",
    "octubre": "10", "noviembre": "11", "diciembre": "12",
    # Português
    "janeiro": "01", "fevereiro": "02", "março": "03",
    "marco": "03", "abril": "04", "maio": "05", "junho": "06",
    "julho": "07", "agosto": "08", "setembro": "09",
    "outubro": "10", "novembro": "11", "dezembro": "12",
}

_DATE_PATTERN = re.compile(
    r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})"
    r"(?:[,\s]+(?:às?\s+)?(\d{1,2}:\d{2}))?",
    re.IGNORECASE,
)


def parse_date(raw: str) -> Optional[str]:
    """
    Converte uma data textual do Moodle em formato ISO 8601.

    Retorna:
        - "YYYY-MM-DDTHH:MM:00" se a hora estiver presente
        - "YYYY-MM-DD"          se apenas a data estiver presente
        - None                  se a string não for reconhecida
    """
    if not raw:
        return None

    match = _DATE_PATTERN.search(raw.lower())
    if not match:
        logger.debug(f"[date_parser] Data não reconhecida: '{raw}'")
        return None

    day   = match.group(1).zfill(2)
    month = _MESES.get(match.group(2), None)
    year  = match.group(3)
    hora  = match.group(4)

    if month is None:
        logger.debug(f"[date_parser] Mês desconhecido: '{match.group(2)}'")
        return None

    if hora:
        return f"{year}-{month}-{day}T{hora}:00"
    return f"{year}-{month}-{day}"
