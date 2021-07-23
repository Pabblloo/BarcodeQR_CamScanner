"""
Система событий (event'ов) для общения scanner-процессов с управляющим процессом
(именно так, в одностороннем порядке от дочернего к управляющему, не наоборот).

События могут содержать как данные для логгирования, так и о событиях, требующих
какого-либо действия со стороны управляющего процесса (напр. перезапуска процесса,
который по какой-либо причине упал, аггрегации QR-кодов с разных камер и т.п.).

Также дочерние процессы не могут писать в единый лог из-за файловых блокировок
и поэтому с помощью событий отправляют запросы на лог в управляющий процесс.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List


@dataclass
class CamScannerEvent:
    """
    Базовый класс для передачи данных от worker-процесса к управляющему процессу.
    Предназначен не для прямого использования, а для наследования.
    """
    LOG_LEVEL: str = field(default='TRACE', repr=False)

    worker_id: Optional[int] = None
    start_time: Optional[datetime] = None
    finish_time: Optional[datetime] = None
    receive_time: Optional[datetime] = None


@dataclass
class EventWithMessage(CamScannerEvent):
    LOG_LEVEL: str = field(default='DEBUG', repr=False)

    message: Optional[str] = None


@dataclass
class TaskError(EventWithMessage):
    """Информация об ошибке из worker-процесса"""
    LOG_LEVEL: str = field(default='ERROR', repr=False)

    message: Optional[str] = None


@dataclass
class TaskResult(CamScannerEvent):
    """Информация о считывании QR- и штрихкода"""
    LOG_LEVEL: str = field(default='DEBUG', repr=False)

    qr_codes: List[str] = field(default_factory=list)
    barcodes: List[str] = field(default_factory=list)


@dataclass
class EndScanning(CamScannerEvent):
    """Завершение сканирования"""
    LOG_LEVEL: str = field(default='INFO', repr=False)


@dataclass
class StartScanning(CamScannerEvent):
    """Начало сканирования"""
    LOG_LEVEL: str = field(default='INFO', repr=False)
