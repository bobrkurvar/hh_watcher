from google import genai
from pydantic import BaseModel, Field
from dto import AIAnalysis, Vacancy
from literals import SYSTEM_INSTRUCTION
import asyncio
import logging
from files import KeyProvider
import textwrap

log = logging.getLogger(__name__)

TARGET_TECHNOLOGIES = [
    "Python",
    "FastAPI",
    "Django",
    "Flask",
    "SQLAlchemy",
    "Alembic",
    "PostgreSQL",
    "Redis",
    "TaskIQ",
    "Celery",
    "REST API",
    "Docker",
    "Nginx",
    "pytest",
    "asyncio",
]

class GeminiSchema(BaseModel):
    batch_index: int = Field(
        description="Номер вакансии из поля ID во входной пачке."
    )

    is_relevant: bool = Field(
        description=(
            "True, если вакансия подходит Python backend-разработчику "
            "по основному стеку, обязанностям и уровню требований. "
            "False, если основная работа не соответствует профилю."
        )
    )

    explanation: str = Field(
        description=(
            "Кратко объясни решение на русском языке. "
            "Укажи решающие требования, технологии и обязанности. "
            "Не приписывай вакансии информацию, которой нет в тексте."
        )
    )

    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description=(
            "Уверенность от 0.0 до 1.0 в правильности значения is_relevant. "
            "0.90–1.00 используй только при прямых и однозначных признаках. "
            "Если требования противоречивы или описание неполное, "
            "используй значение ниже 0.90."
        )
    )


class GeminiAnalyzer:
    def __init__(self):
        self._pool = asyncio.Queue()
        self.key_manager = KeyProvider()
        self._background_tasks = set()
        if not self.key_manager.keys:
            raise RuntimeError("Не найдено ни одного API-ключа Gemini")

        for key in self.key_manager.keys:
            self._pool.put_nowait(genai.Client(api_key=key))
        target_technologies = ", ".join(TARGET_TECHNOLOGIES)
        self.system_instruction = textwrap.dedent(SYSTEM_INSTRUCTION.format(target_technologies=target_technologies)).strip()
        self.limit = None

    def _build_batch_text(self, chunk: list[Vacancy]) -> str:
        batch_text_parts: list[str] = []

        for index, vacancy in enumerate(chunk):
            preview = vacancy.preview
            details = vacancy.details

            batch_text_parts.append(
                f"ID: {index}\n"
                f"Название: {preview.title}\n"
                f"Описание: {details.description}\n"
                f"Ключевые навыки: "
                f"{', '.join(details.key_skills) or 'не указаны'}\n"
                f"Требуемый опыт: {details.experience or 'не указан'}\n"
                f"Тип занятости: {details.employment or 'не указан'}\n"
                f"График: {details.schedule or 'не указан'}\n"
                f"Формат работы: "
                f"{', '.join(details.work_formats) or 'не указан'}"
            )

        return "\n---\n".join(batch_text_parts)

    async def _cooldown_client(self, client: genai.Client):
        log.warning("Ключ поймал ошибку (вероятно 429). Уходит на паузу 60 сек...")
        await asyncio.sleep(60)
        self._pool.put_nowait(client)
        log.debug("Ключ вернулся в пул.")

    async def _process_single_chunk(self, chunk: list[Vacancy], start_index: int) -> list[tuple[int, AIAnalysis]]:
        """Изолированная задача для обработки одной пачки данных."""
        batch_text, retries = self._build_batch_text(chunk), 0

        while retries < 5:
            client = await self._pool.get()
            try:
                response = await client.aio.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=(
                        "Проанализируй следующие вакансии "
                        "и верни массив JSON:\n"
                        f"{batch_text}"
                    ),
                    config={
                        "system_instruction": self.system_instruction,
                        "response_mime_type": "application/json",
                        "response_schema": list[GeminiSchema],
                    },
                )

                if not response.parsed:
                    raise RuntimeError("Gemini вернул пустой ответ или сработал фильтр.")

                parsed_results = []
                for ai_data in response.parsed:
                    if not 0 <= ai_data.batch_index < len(chunk):
                        log.error("Несуществующий batch_index: %s", ai_data.batch_index)
                        continue

                    analysis = AIAnalysis(
                        is_relevant=ai_data.is_relevant,
                        explanation=ai_data.explanation,
                        confidence=ai_data.confidence,
                    )

                    absolute_index = start_index + ai_data.batch_index
                    parsed_results.append((absolute_index, analysis))

                self._pool.put_nowait(client)
                return parsed_results

            except Exception:
                log.exception("Ошибка запроса к Gemini.")
                retries += 1
                task = asyncio.create_task(self._cooldown_client(client))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)
                await asyncio.sleep(0)

        log.error("Пачка заказов (индекс %s) пропущена после %s неудачных попыток.", start_index, retries)
        return []

    async def analyze_vacancies(self, vacancies: list[Vacancy], batch_size: int = 15) -> list[AIAnalysis | None]:
        if not vacancies:
            return []

        result: list[AIAnalysis | None] = [None] * len(vacancies)
        tasks = []

        for chunk_number, start_index in enumerate(range(0, len(vacancies), batch_size)):
            if self.limit is not None and chunk_number >= self.limit:
                break

            chunk = vacancies[start_index:start_index + batch_size]
            tasks.append(self._process_single_chunk(chunk, start_index))

        results = await asyncio.gather(*tasks)
        for chunk_result in results:
            for absolute_index, analysis_obj in chunk_result:
                result[absolute_index] = analysis_obj

        return result
