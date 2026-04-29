from __future__ import annotations
import re
import os
from pathlib import Path
import requests
from deep_translator import GoogleTranslator, single_detection

_MEDIA_IMAGES_DIR = Path(__file__).resolve().parent.parent / "media" / "images"


def translate_to_russian_if_needed(text):
    if not text:
        return text

    try:
        detected_lang = single_detection(text, api_key=None)
        if detected_lang == 'ru':
            return text


        translator = GoogleTranslator(source='auto', target='ru')
        return translator.translate(text)

    except Exception as e:
        print(f"Не удалось перевести текст: {e}")
        return text


def sanitize_filename(filename: str) -> str:
    """Удаляет из строки символы, недопустимые в именах файлов."""
    return re.sub(r'[<>:"/\\|?*]', '', filename).strip()

def download_image(url: str, save_path: str) -> bool:
    try:
        response = requests.get(url, stream=True, timeout=15)
        response.raise_for_status()
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"Ошибка при скачивании изображения: {e}")
        return False

def parse_russian_date(date_str: str) -> str | None:
    if not date_str:
        return None

    month_map = {
        "янв": 1, "фев": 2, "мар": 3, "апр": 4, "мая": 5, "май": 5,
        "июн": 6, "июл": 7, "авг": 8, "сен": 9, "окт": 10, "ноя": 11, "дек": 12
    }

    pattern = r"(\d{1,2})\s+([а-яА-Я]+)\.?\s+(\d{4})\s*г?\.?"
    match = re.search(pattern, date_str.lower())

    if not match:
        return None

    day = int(match.group(1))
    month_abbr = match.group(2).rstrip(".")
    year = int(match.group(3))

    month_num = None
    for key, num in month_map.items():
        if month_abbr.startswith(key):
            month_num = num
            break

    if month_num is None:
        return None

    return f"{year:04d}-{month_num:02d}-{day:02d}"

def convert_percent_to_rating(percent: float | None) -> float | None:
    if percent is None:
        return None
    return round((percent / 100) * 10, 1)

def get_steam_game_data(store_url: str, download_images: bool = True, images_dir: str = "images") -> dict:

    try:
        app_id = store_url.split('/app/')[1].split('/')[0]
    except (IndexError, AttributeError):
        return {"error": "Неверный формат ссылки"}

    app_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}&l=russian"
    try:
        app_response = requests.get(app_url, timeout=10)
        app_response.raise_for_status()
        app_data = app_response.json()
    except requests.exceptions.RequestException as e:
        return {"error": f"Ошибка запроса AppDetails: {e}"}
    except ValueError as e:
        return {"error": f"Ошибка парсинга JSON: {e}"}

    if not app_data.get(str(app_id), {}).get("success"):
        return {"error": f"Не удалось найти игру с App ID {app_id}"}

    game = app_data[str(app_id)]["data"]

    name = game.get("name", "Unknown")
    short_description = game.get("short_description")
    header_image = game.get("header_image")
    store_link = f"https://store.steampowered.com/app/{app_id}"
    raw_release_date = game.get("release_date", {}).get("date")
    release_date = parse_russian_date(raw_release_date)

    reviews_url = f"https://store.steampowered.com/appreviews/{app_id}?json=1&language=all&filter=all"
    try:
        reviews_response = requests.get(reviews_url, timeout=10)
        reviews_response.raise_for_status()
        reviews_data = reviews_response.json()
        summary = reviews_data.get("query_summary", {})
        total_positive = summary.get("total_positive", 0)
        total_reviews = summary.get("total_reviews", 0)
        if total_reviews > 0:
            positive_percent = round((total_positive / total_reviews) * 100, 2)
        else:
            positive_percent = 0.0
        review_score_desc = summary.get("review_score_desc", "Нет данных")
    except (requests.exceptions.RequestException, ValueError) as e:
        positive_percent = None
        review_score_desc = f"Ошибка получения отзывов: {e}"

    rating_out_of_10 = convert_percent_to_rating(positive_percent)

    local_image_path = None
    if download_images and header_image:
        safe_name = sanitize_filename(name.replace(' ', '_'))
        filename = f"{app_id}_{safe_name}.jpg"
        base_dir = Path(images_dir) if images_dir != "images" else _MEDIA_IMAGES_DIR
        save_path = str(base_dir / filename)
        success = download_image(header_image, save_path)
        if success:
            local_image_path = save_path

    # Для админки и JSON: HTTPS URL Steam CDN (превью + скачивание при Save).
    # Локальный путь с другой машины в браузере не работает.
    image_for_form = header_image or ""

    result = {
        "title": name,
        "rating": int(rating_out_of_10 or 0),
        "release": release_date,
        "description": short_description,
        "steam_url": store_link,
        "image_url": image_for_form,
       #"local_image_path": ,
       #"store_link": store_link,
       #"positive_review_percent": positive_percent,
       #"review_score_desc": review_score_desc,
       #"app_id": app_id,
    }

   #if "metacritic" in game:
   #    result["rating"] = f"{game['metacritic']['score']} (Metacritic)"
   #elif "recommendations" in game:
   #    rec = game["recommendations"]
   #    result["rating"] = f"Рекомендаций: {rec.get('total', 0)}"
   #else:
   #    result["rating"] = "Нет данных"

    return result


if __name__ == "__main__":
    print("=== Парсер данных игры из Steam ===\n")
    while True:
        url = input("Введите ссылку на игру в Steam: ").strip()
        if not url:
            print("Введите ссылку на игру в Steam.\n")
            continue

        if "store.steampowered.com/app/" not in url:
            print(
                "Неверный формат. Убедитесь, что это Steam-ссылка.\n")
            continue

        print("\nЗагрузка данных... Подождите.\n")
        data = get_steam_game_data(url)

        if "error" in data:
            print(f"Ошибка: {data['error']}")
        else:
            print(f"1. Название: {data['title']}")
            print(f"2. Оценка: {data['rating']}/10")
            print(f"3. Дата релиза: {data['release']}")
            print(f"4. Краткое описание: {data['description']}")
            print(f"5. URL изображения: {data['image_url']}")
            if data.get('local_image_path'):
                print(f"Изображение сохранено: {data['local_image_path']}")

        again = input("\nОбработать ещё одну игру? (y/n): ").strip().lower()
        if again != 'y':
            print("Выход из программы.")
            break
        print("\n" + "=" * 50 + "\n")