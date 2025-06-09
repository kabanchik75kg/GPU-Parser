import csv
import json
import re
from typing import Dict, List, Tuple, Union

import requests
from bs4 import BeautifulSoup


# Константы
URL = "https://technical.city/ru/video/rating"
HEADERS = {
    "Accept": "*/*",
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"
}


def normalize_value(value: str) -> Union[int, float, str]:
    """Нормализует значение характеристики, преобразуя числа в числовой формат"""
    if not value:
        return value

    # Удаляем скобки и их содержимое
    clean_value = re.sub(r'\([^)]*\)', '', value).strip()

    # Пытаемся извлечь число (учитываем разделители тысяч)
    num_match = re.search(r'[\d,.\s]+', clean_value)
    if num_match:
        num_str = num_match.group(0).replace(',', '.').replace(' ', '')
        try:
            # Пробуем преобразовать в float если есть точка
            if '.' in num_str:
                return float(num_str)
            return int(num_str)
        except ValueError:
            pass

    return clean_value


def filter_gpu(gpu_data: dict, filters: Dict[str, Union[Tuple, str, int]]) -> bool:
    """Проверяет соответствует ли видеокарта заданным фильтрам"""
    for key, filter_value in filters.items():
        actual_value = gpu_data.get(key)

        # Если характеристика отсутствует - не подходит
        if actual_value is None:
            return False

        # Фильтрация по диапазону
        if isinstance(filter_value, tuple):
            min_val, max_val = filter_value

            # Если значение не число - пропускаем
            if not isinstance(actual_value, (int, float)):
                return False

            if not (min_val <= actual_value <= max_val):
                return False

        # Фильтрация по точному значению
        else:
            if str(actual_value) != str(filter_value):
                return False

    return True

# Выполняем код один раз, дальше комитим
# (если удаляется rating.html или cards_text_href.json)

# # Добавим заголовки для того, чтобы сайт не распознал в нас бота
# req = requests.get(url=URL, headers=HEADERS)

# # Содержимое ответа в unicode
# src = req.text

# # Чтобы избежать бан сохраняем код страницы
# with open("rating.html", "w") as file:
#     file.write(src)


# # Сохраним код страницы в переменную
# with open("rating.html") as file:
#     src = file.read()

# # Выбор парсера lxml: скорость + совместимость с BeautifulSoup
# soup = BeautifulSoup(src, "lxml")

# # Выбираем с id = itemrow* (это видеокарты)
# cards_data = soup.select('tr[id^="itemrow"]')

# # Собираем видеокарты в словарь: название: ссылка на видекарту
# cards_text_href = {}
# for card_data in cards_data:
#     card = card_data.find_all("td", limit=2)[1]
#     card_name = card.text
#     card_ref = "https://technical.city" + card.find("a").get("href")
#     cards_text_href[card_name] = card_ref

# with open("cards_text_href.json", "w") as file:
#     json.dump(cards_text_href, file, indent=4, ensure_ascii=False)


# Загружаем файл со списком видеокарт в переменную
with open("cards_text_href.json") as file:
    cards_text_href = json.load(file)

print(f"Найдено {len(cards_text_href)} видеокарт")

# Определяем фильтры
FILTERS = {
    "Количество потоковых процессоров": (10000, 20000)
}

# Список характеристик
CHARACTERISTICS = [
    "Количество потоковых процессоров",
    "Частота ядра",
    "Частота в режиме Boost",
    "Количество транзисторов",
    "Технологический процесс",
    "Энергопотребление (TDP)",
    "Скорость текстурирования",
    "Производительность с плавающей точкой",
    "ROPs",
    "TMUs",
    "Tensor Cores",
    "Ray Tracing Cores"
]

# Создаем CSV файл
with open("filtered_gpus.csv", "w", encoding="utf-8", newline='') as file:
    writer = csv.writer(file)
    # Заголовки: Название, URL + характеристики
    writer.writerow(["Название", "URL"] + CHARACTERISTICS)

count = 0
filtered_count = 0

for card_name, card_href in cards_text_href.items():
    count += 1
    print(f"Обработка ({count}/{len(cards_text_href)}): {card_name}")

    try:
        # Загружаем страницу видеокарты
        req = requests.get(url=card_href, headers=HEADERS)
        req.raise_for_status()
        soup = BeautifulSoup(req.text, "lxml")

        # Собираем характеристики
        gpu_data = {"Название": card_name, "URL": card_href}

        # Пытаемся найти таблицу характеристик
        tables = soup.find_all("table", class_="compare-table")
        if len(tables) < 2:
            print(f"Не найдена таблица характеристик для {card_name}")
            continue

        # Парсим характеристики из таблицы
        rows = tables[1].find('tbody').find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) < 2:
                continue

            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            gpu_data[key] = normalize_value(value)

        # Применяем фильтры
        if filter_gpu(gpu_data, FILTERS):
            filtered_count += 1

            # Подготавливаем строку для CSV
            row_data = [card_name, card_href]
            for char in CHARACTERISTICS:
                row_data.append(gpu_data.get(char, "N/A"))

            # Записываем в CSV
            with open("filtered_gpus.csv", "a", encoding="utf-8", newline='') as file:
                writer = csv.writer(file)
                writer.writerow(row_data)

    except Exception as e:
        print(f"Ошибка при обработке {card_name}: {str(e)}")

print("\n" + "_" * 35 + "\n")
print(f"Обработка завершена! Всего обработано: {count} видеокарт")
print(f"Соответствует фильтру: {filtered_count} видеокарт")
