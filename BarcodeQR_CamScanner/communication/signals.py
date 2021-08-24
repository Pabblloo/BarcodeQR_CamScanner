"""
Функциями для отправки результатов работы
программам извне и получению информации от них.
"""
from json import JSONDecodeError
from typing import List, Optional

import requests
from requests.exceptions import RequestException
from loguru import logger


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
        send_data = {
            'qr': qr_code,
            'barcode': barcode,
        }

        try:
            response = requests.put(success_pack_mapping, json=send_data, timeout=REQUEST_TIMEOUT_SEC)
            response.raise_for_status()
        except RequestException as e:
            logger.error("Ошибка при попытке отправки кодов на сервер")
            logger.opt(exception=e)


def notify_that_no_packdata(domain_url: str) -> None:
    """
    Оповещает сервер, что QR- и штрихкоды не были считаны с текущей пачки.
    """
    logger.debug("Отправка извещения о пачке без данных")

    if get_work_mode(domain_url) == 'auto':
        return None

    # TODO: разобраться в функции ниже (и всём модуле тоже),
    #  проверить правильность, исключения и раскомментировать
    #
    # wERD.snmp_set(er.OID['ALARM-1'], er.on)


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


def get_pack_codes_count(domain_url: str) -> Optional[int]:
    """
    Узнаёт от сервера, сколько QR-кодов ожидать на одной пачке
    """
    global REQUEST_TIMEOUT_SEC
    qr_count_mapping = f'{domain_url}/api/v1_0/current_batch'

    logger.debug("Получение данных об ожидаемом кол-ве QR-кодов")
    try:
        response = requests.get(qr_count_mapping, timeout=REQUEST_TIMEOUT_SEC)
        response.raise_for_status()
    except RequestException as e:
        logger.error("Ошибка при попытке получить от сервера ожидаемое кол-во пачек")
        logger.opt(exception=e)
        return None

    try:
        data = response.json()
    except JSONDecodeError as e:
        logger.error("Ошибка при декодировании JSON-ответа с ожидаемым кол-вом пачек")
        logger.opt(exception=e)
        return None

    packs_in_block = data.get('params', {}).get('multipacks_after_pintset', None)
    if packs_in_block is None:
        logger.error("Ошибка при извлечении из JSON ответа с ожидаемым кол-вом пачек")
        return None
    return int(packs_in_block)
