from __future__ import annotations

import re
from enum import StrEnum


class TitleRejectReason(StrEnum):
    ONE_C = "one_c"
    JAVA = "java"
    DOTNET = "dotnet"
    PHP = "php"
    FRONTEND = "frontend"
    MOBILE = "mobile"
    DEVOPS = "devops"
    QA = "qa"
    DATA = "data"
    CPP = "cpp"
    EMBEDDED = "embedded"


TITLE_REJECT_PATTERNS: dict[TitleRejectReason, tuple[str, ...]] = {
    TitleRejectReason.ONE_C: (
        r"\b1[сc]\b",
        r"\b1[сc][:\s-]?предприятие\b",
        r"\b(?:разработчик|программист|консультант)\s+1[сc]\b",
        r"\b1[сc]\s*(?:разработчик|программист|консультант)\b",
    ),
    TitleRejectReason.JAVA: (
        r"\bjava\s*(?:разработчик|developer|программист)\b",
        r"\b(?:разработчик|developer|программист)\s+java\b",
        r"\bjava\s+backend\b",
        r"\bbackend\s+java\b",
    ),
    TitleRejectReason.DOTNET: (
        r"\b(?:c#|\.net|asp\.net)\s*(?:разработчик|developer|программист)\b",
        r"\b(?:разработчик|developer|программист)\s+(?:c#|\.net|asp\.net)\b",
        r"\bnet\s+developer\b",
    ),
    TitleRejectReason.PHP: (
        r"\bphp\s*(?:разработчик|developer|программист)\b",
        r"\b(?:разработчик|developer|программист)\s+php\b",
        r"\b(?:laravel|symfony|bitrix)\s*(?:разработчик|developer|программист)?\b",
    ),
    TitleRejectReason.FRONTEND: (
        r"\bfront(?:end|[-\s]end)\s*(?:разработчик|developer|программист)?\b",
        r"\b(?:react|angular|vue(?:\.js)?)\s*(?:разработчик|developer|программист)?\b",
        r"\b(?:верстальщик|html[-\s]?верстальщик)\b",
    ),
    TitleRejectReason.MOBILE: (
        r"\b(?:android|ios)\s*(?:разработчик|developer|программист)?\b",
        r"\b(?:mobile|мобильн\w*)\s*(?:разработчик|developer|программист)?\b",
        r"\b(?:swift|kotlin)\s*(?:разработчик|developer|программист)?\b",
    ),
    TitleRejectReason.DEVOPS: (
        r"\bdevops(?:[-\s]?(?:инженер|engineer))?\b",
        r"\b(?:sre|site reliability engineer)\b",
        r"\bсистемн\w*\s+администратор\b",
    ),
    TitleRejectReason.QA: (
        r"\bqa(?:[-\s]?(?:инженер|engineer))?\b",
        r"\b(?:тестировщик|инженер\s+по\s+тестированию)\b",
        r"\bautomation\s+qa\b",
    ),
    TitleRejectReason.DATA: (
        r"\bdata\s+(?:analyst|engineer|scientist)\b",
        r"\b(?:аналитик\s+данных|bi[-\s]?аналитик)\b",
        r"\bml[-\s]?(?:инженер|engineer)\b",
        r"\bmachine learning\b",
    ),
    TitleRejectReason.CPP: (
        r"\bc\+\+\s*(?:разработчик|developer|программист)\b",
        r"\b(?:разработчик|developer|программист)\s+c\+\+\b",
    ),
    TitleRejectReason.EMBEDDED: (
        r"\bembedded\b",
        r"\bвстраиваем\w*\s+систем\b",
        r"\b(?:разработчик|инженер)\s+прошивок\b",
        r"\bмикроконтроллер\w*\b",
    ),
}


COMPILED_TITLE_REJECT_PATTERNS: dict[TitleRejectReason, tuple[re.Pattern[str], ...]] = {
    reason: tuple(re.compile(pattern, re.IGNORECASE) for pattern in patterns)
    for reason, patterns in TITLE_REJECT_PATTERNS.items()
}


def normalize_title(title: str) -> str:
    return " ".join(title.lower().replace("ё", "е").split())


def find_title_reject_reason(title: str) -> TitleRejectReason | None:
    normalized_title = normalize_title(title)

    for reason, patterns in COMPILED_TITLE_REJECT_PATTERNS.items():
        if any(pattern.search(normalized_title) for pattern in patterns):
            return reason

    return None