import httpx
import asyncio
from core import conf


async def get_app_token():

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://hh.ru/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": conf.client_id,
                "client_secret": conf.client_secret,
            }
        )
        print("Статус ответа:", response.status_code)

        if response.status_code == 200:
            print("\n✅ Твой Access Token:")
            print(response.json().get("access_token"))
        else:
            print("Ошибка:", response.text)


if __name__ == "__main__":
    asyncio.run(get_app_token())