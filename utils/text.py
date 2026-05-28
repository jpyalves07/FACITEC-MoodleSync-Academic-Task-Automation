"""
utils/text.py
─────────────
Funções auxiliares para limpeza e normalização de strings
extraídas via Selenium (textos do DOM HTML do Moodle).
"""

import re
from typing import Optional


def clean(text: Optional[str]) -> str:
    """Remove espaços extras e quebras de linha de uma string."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip())


def clean_task_title(text: Optional[str]) -> str:
    """
    Remove sufixos que o Moodle anexa ao nome da tarefa no card do curso.
    O Moodle concatena o tipo de atividade após uma quebra de linha,
    por exemplo: 'FT 03_HTI Ejercitario UA3\\nTarea'.

    Retorna apenas a primeira linha, que é o título real da tarefa.
    """
    if not text:
        return ""
    # Tudo após a primeira quebra de linha é sufixo do tipo de atividade
    title = text.split("\n")[0]
    return re.sub(r"\s+", " ", title.strip())
