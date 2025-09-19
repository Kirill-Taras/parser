import json
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

# URL страницы с меню
URL = os.getenv("MENU_URL")
if not URL:
    raise RuntimeError("❌ Не задан URL для парсинга в .env")

IMAGES_DIR = Path("images")
IMAGES_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/140.0.0.0 Safari/537.36"
    ),
    "Referer": "https://www.syrovarnya.com/",
    "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
}


def fetch_data(url: str) -> dict | None:
    """
    Делает HTTP-запрос к API и возвращает JSON.

    Args:
        url (str): URL API.

    Returns:
        dict | None: JSON-ответ или None, если запрос не удался.
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        print("✅ Данные успешно получены!")
        return response.json()
    except requests.RequestException as e:
        print(f"❌ Ошибка запроса страницы: {e}")
        return None


def download_image(url: str, filename: str) -> str | None:
    """
    Скачивает изображение и сохраняет в папку images.

    Args:
        url (str): ссылка на картинку.
        filename (str): имя файла.

    Returns:
        str | None: путь к файлу или None, если ошибка.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        filepath = IMAGES_DIR / filename
        with open(filepath, "wb") as f:
            f.write(response.content)
        return str(filepath)
    except requests.RequestException as e:
        print(f"⚠️ Ошибка скачивания {url}: {e}")
        return None


def parse_menu(data: dict) -> list[dict]:
    """
    Парсит меню из JSON в удобную структуру.

    Args:
        data (dict): JSON-ответ от API.

    Returns:
        list[dict]: список категорий с блюдами.
    """
    result = []
    try:
        categories = data["pageProps"]["catalog"]["catalog"]
    except (KeyError, TypeError):
        print("❌ Неверный формат JSON")
        return result

    for category in categories:
        category_name = category.get("name", "Без категории")
        items = []

        for item in category.get("items", []):
            title = item.get("title", "Без названия")
            desc = item.get("body_split") or item.get("body") or "Нет описания"
            weight = f"{item.get('weight', '')} {item.get('unit', '')}".strip()
            variations = json.loads(item.get("variations", "[]"))
            price = variations[0]["price"] if variations else "нет данных"

            photo_url = item.get("photo")
            photo_path = None
            if photo_url:
                ext = photo_url.split("?")[0].split(".")[-1]  # jpg/png
                safe_name = f"{item['id']}.{ext}"
                photo_path = download_image(photo_url, safe_name)

            items.append(
                {
                    "title": title,
                    "desc": desc,
                    "weight": weight,
                    "price": price,
                    "photo": photo_path or photo_url,
                }
            )

        result.append({"category": category_name, "items": items})

    return result


if __name__ == "__main__":
    data = fetch_data(URL)
    if data:
        menu = parse_menu(data)

        # Выведем красиво
        for category in menu:
            print(f"\n📌 Категория: {category['category']}")
            for item in category["items"]:
                print(f"  🍴 {item['title']}")
                print(f"     Описание: {item['desc']}")
                print(f"     Граммовка: {item['weight']}")
                print(f"     Цена: {item['price']} ₽")
        # Сохраним меню в JSON для бота
        with open("menu.json", "w", encoding="utf-8") as f:
            json.dump(menu, f, ensure_ascii=False, indent=4)

        print("✅ Меню сохранено в menu.json и картинки скачаны в папку images/")
