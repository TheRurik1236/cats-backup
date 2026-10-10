import json
import logging
import time
from urllib.parse import quote

import requests

GROUP_NAME = 'PYAPI-160'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')


class CatsAPI:
    """Получение картинок с котами с сайта cataas.com."""

    def __init__(self):
        self.base_url = 'https://cataas.com'

    def get_cat(self, text):
        """Получить информацию о картинке кота с текстом."""
        url = f'{self.base_url}/cat/says/{quote(text)}'
        response = requests.get(url, params={'json': 'true'})
        if response.status_code != 200:
            logging.error(f'Не удалось получить кота: {response.status_code}')
            return None
        return response.json()


class YandexDisk:
    """Работа с REST API Яндекс.Диска."""

    def __init__(self, token):
        self.base_url = 'https://cloud-api.yandex.net/v1/disk/resources'
        self.headers = {'Authorization': f'OAuth {token}'}

    def create_folder(self, folder_name):
        """Создать папку на диске."""
        response = requests.put(self.base_url,
                                params={'path': folder_name},
                                headers=self.headers)
        if response.status_code == 201:
            logging.info(f'Папка {folder_name} создана')
        elif response.status_code == 409:
            logging.info(f'Папка {folder_name} уже существует')
        elif response.status_code == 401:
            logging.error('Неверный токен Яндекс.Диска')
            return False
        else:
            logging.error(f'Ошибка создания папки: {response.status_code}')
            return False
        return True

    def upload_from_url(self, url, path):
        """Загрузить файл на диск по ссылке."""
        response = requests.post(f'{self.base_url}/upload',
                                 params={'url': url, 'path': path},
                                 headers=self.headers)
        if response.status_code == 409:
            logging.error(f'Файл {path} уже есть на диске')
            return False
        if response.status_code != 202:
            logging.error(f'Ошибка загрузки: {response.status_code}')
            return False

        # Диск скачивает картинку сам, ждём, пока он закончит
        operation_url = response.json()['href']
        status = 'in-progress'
        while status == 'in-progress':
            time.sleep(1)
            response = requests.get(operation_url, headers=self.headers)
            status = response.json()['status']
            logging.info(f'Статус загрузки: {status}')

        if status != 'success':
            logging.error('Яндекс.Диск не смог скачать картинку с cataas.com')
            return False
        return True

    def get_file_size(self, path):
        """Узнать размер файла на диске."""
        response = requests.get(self.base_url, params={'path': path},
                                headers=self.headers)
        return response.json()['size']


def main():
    text = input('Введите текст для картинки: ').strip()
    token = input('Введите токен Яндекс.Диска: ').strip()
    if not text or not token:
        logging.error('Текст и токен не должны быть пустыми')
        return

    cats_api = CatsAPI()
    yandex_disk = YandexDisk(token)

    logging.info(f'Создаю папку {GROUP_NAME} на Яндекс.Диске')
    if not yandex_disk.create_folder(GROUP_NAME):
        return

    logging.info(f'Получаю кота с текстом "{text}"')
    cat = cats_api.get_cat(text)
    if cat is None:
        return

    extension = cat['mimetype'].split('/')[-1]
    file_name = f'{text}.{extension}'
    file_path = f'{GROUP_NAME}/{file_name}'

    logging.info(f'Загружаю {file_name} на Яндекс.Диск')
    if not yandex_disk.upload_from_url(cat['url'], file_path):
        return

    size = yandex_disk.get_file_size(file_path)
    logging.info(f'Картинка загружена, размер {size} байт')

    with open('result.json', 'w', encoding='utf-8') as file:
        json.dump([{'file_name': file_name, 'size': size}], file,
                  ensure_ascii=False, indent=2)
    logging.info('Информация о файле сохранена в result.json')


if __name__ == '__main__':
    main()
