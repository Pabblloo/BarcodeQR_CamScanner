"""Скрипт для запуска чтения с камеры"""

from dotenv import load_dotenv

from scan_with_1_camera import run


if __name__ == '__main__':
    load_dotenv()
    run()
