import httpx

from dto import VacancyPreview
from core import conf


class HHClient:
    BASE_URL = "https://api.hh.ru"

    def __init__(self) -> None:
        headers = {
            "User-Agent": "hh_watcher/0.1 (andrey.bogdanov2005@mail.ru)",
            "Authorization": f"Bearer {conf.access_token}",
        }
        self._client = httpx.AsyncClient(
            base_url=self.BASE_URL,
            headers=headers,
            timeout=20.0,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_vacancies(
        self,
        query: str,
    ) -> list[VacancyPreview]:
        vacancies: list[VacancyPreview] = []
        page = 0

        while True:
            response = await self._client.get(
                "/vacancies",
                params={
                    "text": query,
                    "page": page,
                    "per_page": 100,
                },
            )
            if response.is_error:
                print(response.status_code)
                print(response.text)
            response.raise_for_status()

            payload = response.json()

            vacancies.extend(
                VacancyPreview.from_api(
                    item,
                    query=query,
                )
                for item in payload["items"]
            )

            if page + 1 >= payload["pages"]:
                break

            page += 1

        return vacancies
