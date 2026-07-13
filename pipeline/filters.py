import re
from dto import VacancyPreview
from filter_keywords import CONTENT_KEYWORDS, EXCLUDED_KEYWORDS
from utils import clean_html

import logging

log = logging.getLogger(__name__)

COMPILED_EXCLUDE_PATTERNS = [
    (word, re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE))
    for word in EXCLUDED_KEYWORDS
]

COMPILED_INCLUDE_PATTERNS = [
    re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) for word in CONTENT_KEYWORDS
]



def apply_soft_filter(raw_text: str):
    clean_text = clean_html(raw_text)
    found_stop_word = None
    for word, pattern in COMPILED_EXCLUDE_PATTERNS:
        if pattern.search(clean_text):
            found_stop_word = word
            break

    if not found_stop_word:
        return True

    for pattern in COMPILED_INCLUDE_PATTERNS:
        if pattern.search(clean_text):
            return True
    # Если True - то не подлежит фильтрации
    return False


def passes_vacancy_preview_filter(vacancy: VacancyPreview) -> bool:
    raw_text = (
        f"{vacancy.title} {vacancy.requirement or ''} {vacancy.responsibility or ''}"
    )
    return apply_soft_filter(raw_text)


def passes_vacancy_details_filter(title: str, description: str, key_skills: list[str]):
    raw_text = " ".join([title, description, *key_skills])
    return apply_soft_filter(raw_text)
