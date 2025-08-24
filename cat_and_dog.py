import requests
import json
import os
import time
from tqdm import tqdm
from urllib.parse import quote

class YandexDisk:
    BASE_URL = 'https://cloud-api.yandex.net/v1/disk/resources'

    def __init__(self, token):
        self.token = token
        self.headers = {
            'Authorization': f'OAuth {self.token}',
            'Content-Type': 'application/json'
        }

    def create_folder(self, path):
        # Создание папки на Яндекс.Диске
        url = self.BASE_URL
        params = {'path': path}
        response = requests.put(url, headers=self.headers, params=params)
        return response.status_code in [201, 409]  # 201 - создана, 409 - уже существует

    def upload_from_url(self, url, path):
        # Загрузка файла на Яндекс.Диск
        upload_url = f'{self.BASE_URL}/upload'
        params = {'url': url, 'path': path}
        response = requests.post(upload_url, headers=self.headers, params=params)
        return response.json()

def clean_filename(name):
    # Очистка имени файла от недопустимых символов
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        name = name.replace(char, '')
    return name

def get_cat_image(text):
    # Получение изображения кота
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

            return {
                'url': image_url,
                'size': size,
                'name': clean_filename(text) + '.jpg'
            }
    except Exception as e:
        print(f'Ошибка при получении изображения кота: {e}')
    return None

def get_dog_images(breed):
    # Получение изображений собаки указанной породы
    try:
        response = requests.get(f'https://dog.ceo/api/breed/{breed}/list', timeout=10)
        if response.status_code != 200:
            return []

        sub_breeds = response.json().get('message', [])
        images = []

        # Основная порода
        if not sub_breeds:
            response = requests.get(f'https://dog.ceo/api/breed/{breed}/images/random', timeout=10)
            if response.status_code == 200:
                data = response.json()
                images.append({
                    'url': data['message'],
                    'sub_breed': None,
                    'breed': breed
                })
        else:
            # Подпороды
            for sub_breed in sub_breeds:
                response = requests.get(f'https://dog.ceo/api/breed/{breed}/{sub_breed}/images/random', timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    images.append({
                        'url': data['message'],
                        'sub_breed': sub_breed,
                        'breed': breed
                    })
        return images
    except Exception as e:
        print(f'Ошибка при получении изображений собак: {e}')
        return []

def main():
    results = []
    print('Выберите задание:')
    print('1. Кошки(cataas.com)')
    print('2. Собаки(dog.ceo)')

    choice = input('Введите номер задания (1 или 2): ')
    token = input('Введите токен для Яндекс.Диска: ')
    yandex = YandexDisk(token)

    if choice == '1':
        # Кошки
        group_id = input('Введите название группы: ')
        text = input('Введите текст для картинки с котиком: ')

        # Создание папки на Яндекс.Диске
        if not yandex.create_folder(group_id):
            print('Ошибка при создании папки')
            return

        # Получение изображения кота
        image_info = get_cat_image(text)
        if not image_info:
            print('Не удалось получить изображение кота')
            return

        # Загрузка изображения на Яндекс.Диск
        path = f'{group_id}/{image_info["name"]}'
        upload_result = yandex.upload_from_url(image_info['url'], path)

        if 'error' not in upload_result:
            results.append({
                'file_name': image_info['name'],
                'size': image_info['size'],
                'path': path
            })
            print(f'Файл {image_info["name"]} загружен на Яндекс.Диск')
        else:
            print(f'Ошибка при загрузке файла {image_info["name"]}: {upload_result["error"]}')

        # Сохранение результатов в json
        with open('results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print('Результаты сохранены в results.json')

    elif choice == '2':
        # Собаки
        breed = input('Введите породу собаки: ')

        # Создание папки на Яндекс.Диске
        if not yandex.create_folder(breed):
            print('Ошибка при создании папки')
            return

        # Получение изображений собаки
        images = get_dog_images(breed)
        if not images:
            print('Не удалось найти изображения указанной породы')
            return

        print(f'Найдено {len(images)} изображений:')

        # Загрузка изображений на Яндекс.Диск
        for image in tqdm(images, desc='Загрузка изображений'):
            if image['sub_breed']:
                file_name = f"{image['breed']}_{image['sub_breed']}_{os.path.basename(image['url'])}"
            else:
                file_name = f"{image['breed']}_{os.path.basename(image['url'])}"

            filename = clean_filename(file_name)
            path = f'{breed}/{filename}'

            upload_result = yandex.upload_from_url(image['url'], path)

            if 'error' not in upload_result:
                # Получение размера файла
                try:
                    size_response = requests.head(image['url'], timeout=10)
                    size = size_response.headers.get('Content-Length', 0)
                except Exception as e:
                    print(f'Ошибка при получении размера файла: {e}')
                    size = 0

                results.append({
                    'file_name': filename,
                    'size': int(size),
                    'path': path,
                    'breed': image['breed'],
                    'sub_breed': image['sub_breed']
                })

            time.sleep(1)  # Задержка между запросами

        # Сохранение результатов в json
        with open('results.json', 'w') as f:
            json.dump(results, f, indent=2)
        print('Результаты сохранены в results.json')

if __name__ == '__main__':
    main()