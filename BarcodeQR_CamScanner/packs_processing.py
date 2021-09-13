"""
Очереди обработки результатов от камер
"""
import abc
from collections import deque
from datetime import timedelta, datetime
from typing import Iterable

from loguru import logger

from .event_system._events import *
from .event_system.handling import BaseEvent


class BaseResultProcessingQueue(metaclass=abc.ABCMeta):
    """
    Базовый абстрактный класс для очередей синхронизации
    данных пачек из разных источников
    """

    @abc.abstractmethod
    def enqueue(self, result: CameraPackResult) -> None:
        """
        Добавление результата в очередь для дальнейшего сопоставления
        с другими результатами
        """

    @abc.abstractmethod
    def get_processed_latest(self) -> Iterable[BaseEvent]:
        """
        Синхронизирует последние результаты из очереди
        и возвращает последовательность с результатами их синхронизации
        """


class InstantCameraProcessingQueue(BaseResultProcessingQueue):
    """
    Очередь для обработки результатов с одной камеры.
    Хранит, валидирует результаты и возвращает соответствующие
    """
    _queue: deque[CameraPackResult]

    def __init__(self):
        self._queue = deque()

    def enqueue(self, result: CameraPackResult) -> None:
        """
        Обрабатывает полученную от сканера запись с QR- и шрихкодами.
        Добавляет её в очередь для обработки.
        """
        self._queue.append(result)

    def get_processed_latest(self) -> list[BaseEvent]:
        """Валидирует пачки с одной камеры"""
        processed = []

        for pack in self._queue:
            qr_codes = pack.qr_codes
            barcodes = pack.barcodes

            if len(qr_codes) == 0:
                logger.debug("Пачка без QR кодов")
                processed.append(PackBadCodes(
                    qr_codes=qr_codes,
                    barcodes=barcodes,
                ))
                continue

            if len(barcodes) == 0:
                logger.debug("Пачка с QR кодами, но без штрихкодов")
                processed.append(PackBadCodes(
                    qr_codes=qr_codes,
                    barcodes=barcodes,
                ))
                continue

            missed_barcodes_count = len(qr_codes) - len(barcodes)
            barcodes += barcodes[-1:] * missed_barcodes_count

            if len(qr_codes) != pack.expected_codes_count:
                logger.debug(f"Ожидалось {pack.expected_codes_count} кодов, "
                             f"но с пачки считалось {len(qr_codes)}")
                processed.append(PackBadCodes(
                    qr_codes=qr_codes,
                    barcodes=barcodes,
                ))
                continue

            processed.append(PackWithCodes(
                qr_codes=qr_codes,
                barcodes=barcodes,
            ))

        self._queue.clear()
        return processed
