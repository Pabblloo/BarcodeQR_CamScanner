"""
Функции для отправки результатов работы
программам извне и получению информации от них.
"""
from json import JSONDecodeError
from typing import List, Optional

import requests
from loguru import logger
from requests.exceptions import RequestException


REQUEST_TIMEOUT_SEC = 2


def notify_about_packdata(
        domain_url: str,
        qr_codes: List[str],
        barcodes: List[str],
) -> None:
    """
    Оповещает сервер, что QR- и штрихкоды успешно считаны с пачки.
    Считанные данные также отправляются серверу.
    """
    global REQUEST_TIMEOUT_SEC
    success_pack_mapping = f'{domain_url}/api/v1_0/new_pack_after_pintset'

    logger.debug(f"Отправка данных пачки на сервер: QR-коды: {qr_codes} штрих-коды: {barcodes}")

    for qr_code, barcode in zip(qr_codes, barcodes):
        send_data = dict(qr=qr_code, barcode=barcode)

        try:
            response = requests.put(success_pack_mapping, json=send_data, timeout=REQUEST_TIMEOUT_SEC)
            response.raise_for_status()
        except RequestException as e:
            logger.error(f"Ошибка при попытке отправки пары кодов (QR='{qr_code}' BAR='{barcode}') на сервер")
            logger.opt(exception=e)


def notify_about_bad_packdata(domain_url: str) -> None:
    """
    Оповещает сервер, что QR- и штрихкоды не были считаны с пачки
    """
    global REQUEST_TIMEOUT_SEC
    # TODO: указать адрес ниже
    bad_pack_mapping = f'{domain_url}/api/v1_0/!!__TODO__FILL_ME_!!'
    logger.warning("Путь для запросов не задан!")

    logger.debug("Отправка извещения о пачке с некорректными кодами")
    try:
        response = requests.post(bad_pack_mapping, timeout=REQUEST_TIMEOUT_SEC)
        response.raise_for_status()
    except RequestException as e:
        logger.error("Ошибка при попытке отправки извещения о бракованной пачке на сервер")
        logger.opt(exception=e)


def get_work_mode(domain_url: str) -> Optional[str]:
    """
    Получает режим работы (в оригинале "записи"!?) с сервера.
    """
    global REQUEST_TIMEOUT_SEC
    wmode_mapping = f'{domain_url}/api/v1_0/get_mode'

    logger.debug("Получение данных о текущем режиме записи")
    try:
        response = requests.get(wmode_mapping, timeout=REQUEST_TIMEOUT_SEC)
        response.raise_for_status()
    except RequestException as e:
        logger.error("Ошибка при попытке получить режим работы с сервера")
        logger.opt(exception=e)
        return None

    try:
        work_mode = response.json()['work_mode']
    except (JSONDecodeError, KeyError) as e:
        logger.error("Ошибка при попытке получить режим работы с сервера")
        logger.opt(exception=e)
        return None

    return work_mode
