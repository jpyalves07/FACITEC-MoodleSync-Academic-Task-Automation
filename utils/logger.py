"""
utils/logger.py
───────────────
Configura e expõe o logger centralizado da aplicação.
Grava simultaneamente no console e em arquivo rotativo.
"""

import logging
import os
from logging.handlers import RotatingFileHandler

from config.settings import DEBUG, LOG_FILE


def setup_logger(name: str = "MoodleSync") -> logging.Logger:
    """
    Cria e configura o logger principal.
    Nível DEBUG se DEBUG=true no .env, caso contrário INFO.
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        # Evita adicionar handlers duplicados em reexecuções
        return logger

    level = logging.DEBUG if DEBUG else logging.INFO
    logger.setLevel(level)

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)-8s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Handler: console
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler: arquivo rotativo (máximo 5 MB, mantém 3 backups)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    file_handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


# Logger padrão — importado pelos demais módulos
logger = setup_logger()
