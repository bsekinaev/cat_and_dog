import requests
import json
import os
import time
from tqdm import tqdm
from urllib.parse import quote
import sys

class YandexDisk:
    BASE_URL = 'https://cloud-api.yandex.net/v1/disk/resources'

    def __init__(self, token):
        self.token = token
        self.headers = {
            'Authorization': f'OAuth {self.token}',
            'Content-Type': 'application/json'
        }

    def create_folder(self, path):
        """Создание папки на Яндекс.Диске с обработкой ошибок"""
        try:
            url = self.BASE_URL
            params = {'path': path}
            response = requests.put(url, headers=self.headers, params=params, timeout=10)

            if response.status_code in [201, 409]:  # 201 - создана, 409 - уже существует
                return True
            else:
                print(f"Ошибка при создании папки: {response.json().get('message', 'Неизвестная ошибка')}")
                return False
        except requests.exceptions.RequestException as e:
            print(f"Сетевая ошибка при создании папки: {e}")
            return False

    def upload_from_url(self, url, path):
        """Загрузка файла на Яндекс.Диск с обработкой ошибок"""
        try:
            upload_url = f'{self.BASE_URL}/upload'
            params = {'url': url, 'path': path}
            response = requests.post(upload_url, headers=self.headers, params=params, timeout=30)
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Сетевая ошибка при загрузке файла: {e}")
            return {'error': str(e)}

def clean_filename(name):
    """Очистка имени файла от недопустимых символов"""
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    # Ограничиваем длину имени файла
    if len(name) > 100:
        name = name[:100]
    return name

def get_cat_images(text, count=1):
    """Получение нескольких изображений кошек с текстом"""
    images = []

    for i in range(count):
        try:
            encoded_text = quote(text)
            url = f'https://cataas.com/cat/says/{encoded_text}?json=true'
            response = requests.get(url, timeout=10)

            if response.status_code == 200:
                data = response.json()
                image_path = data.get('url', '')

                if image_path.startswith('http'):
                    image_url = image_path
                else:
                    image_url = f'https://cataas.com{image_path}'

                # Получаем размер изображения
                try:
                    head_response = requests.head(image_url, timeout=10)
                    size = head_response.headers.get('Content-Length', 0)
                except Exception as e:
                    print(f'Ошибка при получении размера изображения: {e}')
                    size = 0

                # Создаем уникальное имя файла для каждого изображения
                filename_suffix = f"_{i+1}" if count > 1 else ""
                file_name = clean_filename(text) + filename_suffix + '.jpg'

                images.append({
                    'url': image_url,
                    'size': size,
                    'name': file_name
                })
            else:
                print(f"Ошибка API cataas.com: {response.status_code}")

        except Exception as e:
            print(f'Ошибка при получении изображения кота: {e}')

        # Небольшая задержка между запросами
        if i < count - 1:
            time.sleep(1)

    return images

def get_dog_images(breed, count_per_breed=1):
    """Получение изображений собак указанной породы"""
    images = []

    try:
        # Получаем список подпород
        response = requests.get(f'https://dog.ceo/api/breed/{breed}/list', timeout=10)
        if response.status_code != 200:
            print(f"Ошибка при получении списка пород: {response.status_code}")
            return []

        sub_breeds = response.json().get('message', [])

        # Если нет подпород, работаем с основной породой
        breeds_to_process = [breed] if not sub_breeds else [f"{breed}/{sub_breed}" for sub_breed in sub_breeds]

        # Для каждой породы/подпороды получаем указанное количество изображений
        for current_breed in breeds_to_process:
            for i in range(count_per_breed):
                try:
                    response = requests.get(f'https://dog.ceo/api/breed/{current_breed}/images/random', timeout=10)
                    if response.status_code == 200:
                        data = response.json()

                        # Определяем, является ли текущая порода подпородой
                        breed_parts = current_breed.split('/')
                        main_breed = breed_parts[0]
                        sub_breed = breed_parts[1] if len(breed_parts) > 1 else None

                        # Получаем размер изображения
                        try:
                            head_response = requests.head(data['message'], timeout=10)
                            size = head_response.headers.get('Content-Length', 0)
                        except Exception as e:
                            print(f'Ошибка при получении размера изображения: {e}')
                            size = 0

                        # Формируем имя файла
                        base_name = os.path.basename(data['message'])
                        if sub_breed:
                            file_name = f"{main_breed}_{sub_breed}_{i+1}_{base_name}"
                        else:
                            file_name = f"{main_breed}_{i+1}_{base_name}"

                        images.append({
                            'url': data['message'],
                            'size': size,
                            'name': clean_filename(file_name),
                            'breed': main_breed,
                            'sub_breed': sub_breed
                        })
                    else:
                        print(f"Ошибка API dog.ceo для породы {current_breed}: {response.status_code}")

                except Exception as e:
                    print(f'Ошибка при получении изображения собаки: {e}')

                # Небольшая задержка между запросами
                if i < count_per_breed - 1 or current_breed != breeds_to_process[-1]:
                    time.sleep(0.5)

    except Exception as e:
        print(f'Общая ошибка при получении изображений собак: {e}')

    return images

def print_header():
    """Вывод заголовка программы"""
    print("=" * 50)
    print("       РЕЗЕРВНОЕ КОПИРОВАНИЕ ИЗОБРАЖЕНИЙ")
    print("=" * 50)
    print()

def print_menu():
    """Вывод меню выбора"""
    print("Выберите задание:")
    print("1. Кошки (cataas.com)")
    print("2. Собаки (dog.ceo)")
    print("3. Выход")
    print()

def get_user_choice():
    """Получение выбора пользователя с проверкой"""
    while True:
        try:
            choice = input("Введите номер задания (1-3): ")
            if choice in ['1', '2', '3']:
                return choice
            else:
                print("Пожалуйста, введите число от 1 до 3.")
        except KeyboardInterrupt:
            print("\nПрограмма прервана пользователем.")
            sys.exit(0)

def get_number_input(prompt, default=1, min_val=1, max_val=50):
    """Получение числового ввода от пользователя с проверкой"""
    while True:
        try:
            value = input(f"{prompt} (по умолчанию {default}): ")
            if not value:
                return default
            value = int(value)
            if min_val <= value <= max_val:
                return value
            else:
                print(f"Пожалуйста, введите число от {min_val} до {max_val}.")
        except ValueError:
            print("Пожалуйста, введите целое число.")
        except KeyboardInterrupt:
            print("\nПрограмма прервана пользователем.")
            sys.exit(0)

def main():
    """Основная функция программы"""
    print_header()

    while True:
        print_menu()
        choice = get_user_choice()

        if choice == '3':
            print("Выход из программы.")
            break

        token = input("Введите токен для Яндекс.Диска: ")
        if not token:
            print("Токен не может быть пустым.")
            continue

        yandex = YandexDisk(token)
        results = []

        if choice == '1':
            # Обработка кошек
            group_id = input("Введите название группы: ")
            text = input("Введите текст для картинки с котиком: ")
            count = get_number_input("Сколько изображений загрузить?", 1, 1, 20)

            # Создание папки на Яндекс.Диске
            if not yandex.create_folder(group_id):
                print("Не удалось создать папку. Проверьте токен и права доступа.")
                continue

            # Получение изображений кошек
            print(f"Получаем {count} изображений кошек...")
            images = get_cat_images(text, count)

            if not images:
                print("Не удалось получить изображения кошек.")
                continue

            # Загрузка изображений на Яндекс.Диск
            print(f"Загружаем {len(images)} изображений на Яндекс.Диск...")
            for image in tqdm(images, desc="Загрузка изображений"):
                path = f'{group_id}/{image["name"]}'
                upload_result = yandex.upload_from_url(image['url'], path)

                if 'error' not in upload_result:
                    results.append({
                        'file_name': image['name'],
                        'size': image['size'],
                        'path': path
                    })
                else:
                    print(f"Ошибка при загрузке файла {image['name']}: {upload_result.get('error', 'Неизвестная ошибка')}")

        elif choice == '2':
            # Обработка собак
            breed = input("Введите породу собаки на английском языке: ")
            count = get_number_input("Сколько изображений для каждой породы/подпороды загрузить?", 1, 1, 10)

            # Создание папки на Яндекс.Диске
            if not yandex.create_folder(breed):
                print("Не удалось создать папку. Проверьте токен и права доступа.")
                continue

            # Получение изображений собак
            print(f"Получаем изображения породы {breed}...")
            images = get_dog_images(breed, count)

            if not images:
                print(f"Не удалось найти изображения породы {breed}.")
                continue

            # Загрузка изображений на Яндекс.Диск
            print(f"Загружаем {len(images)} изображений на Яндекс.Диск...")
            for image in tqdm(images, desc="Загрузка изображений"):
                path = f'{breed}/{image["name"]}'
                upload_result = yandex.upload_from_url(image['url'], path)

                if 'error' not in upload_result:
                    results.append({
                        'file_name': image['name'],
                        'size': image['size'],
                        'path': path,
                        'breed': image.get('breed', ''),
                        'sub_breed': image.get('sub_breed', '')
                    })
                else:
                    print(f"Ошибка при загрузке файла {image['name']}: {upload_result.get('error', 'Неизвестная ошибка')}")

        # Сохранение результатов в JSON
        if results:
            try:
                with open('results.json', 'w', encoding='utf-8') as f:
                    json.dump(results, f, indent=2, ensure_ascii=False)
                print(f"Результаты сохранены в файл results.json ({len(results)} записей).")
            except Exception as e:
                print(f"Ошибка при сохранении результатов: {e}")
        else:
            print("Нет результатов для сохранения.")

        print()
        continue_input = input("Хотите выполнить еще одну операцию? (y/n): ")
        if continue_input.lower() != 'y':
            print("Выход из программы.")
            break

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\nПрограмма прервана пользователем.")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")