import re
from dto import VacancyPreview
from filter_keywords import CONTENT_KEYWORDS, EXCLUDED_KEYWORDS

COMPILED_EXCLUDE_PATTERNS = [
    (word, re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE)) 
    for word in EXCLUDED_KEYWORDS
]

COMPILED_INCLUDE_PATTERNS = [
    re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE) 
    for word in CONTENT_KEYWORDS
]

def clean_html(text: str) -> str:
    return re.sub(r'<[^>]+>', '', text)


def apply_soft_filter(vacancy: VacancyPreview) -> bool:
    raw_text = f"{vacancy.title} {vacancy.requirement or ''} {vacancy.responsibility or ''}"
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