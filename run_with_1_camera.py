"""Скрипт для запуска чтения с камеры"""

from dotenv import load_dotenv

from scan_with_2_cameras import main


if __name__ == '__main__':
    load_dotenv()
    main()
