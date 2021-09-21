"""
Классы для распознавания различных явлений и критериев на изображениях.

Например:
    - движение
    - отличие предыдущего кадра от следующего
    - отличие изображения от эталона
    - отличие картинки от фона последних изображений
    - и т.п.
"""
import abc
from typing import Optional

import cv2
import numpy as np
import pysnmp.hlapi as snmp
from tensorflow.lite.python.interpreter import Interpreter

from ._evaluation_methods import (get_neuronet_score, get_mog2_foreground_score)


class BaseRecognizer(metaclass=abc.ABCMeta):
    """
    Базовый абстрактный класс для всех распознавателей с изображений
    """

    @abc.abstractmethod
    def is_recognized(self, image: np.ndarray) -> bool:
        """
        Получает текующую оценку изображения по критерию
        """


class NeuronetPackRecognizer(BaseRecognizer):
    """
    Определитель наличия пачки на изображении. Получает предсказания от нейросети.

    **Осторожно: очень медленно работает**

    Parameters:
        model_path: путь к ``TF-Lite Flatbuffer`` файлу
        threshold_value: пороговое значение для активации критерия

    Attributes:
        _THRESHOLD_SCORE: пороговое значение, меньше которого
            ``is_recognized`` будет возвращать ``False``
    """
    _interpreter: Interpreter
    _THRESHOLD_SCORE: float
    _image: Optional[np.ndarray]

    def __init__(self, model_path: str, threshold_value: float = 0.6):
        self._THRESHOLD_SCORE = threshold_value
        self._interpreter = Interpreter(model_path=model_path)
        self._interpreter.allocate_tensors()

    def is_recognized(self, image: np.ndarray) -> bool:
        score = get_neuronet_score(self._interpreter, image)
        return score > self._THRESHOLD_SCORE


class BSPackRecognizer(BaseRecognizer):
    """
    Распознаватель пачек, посредством сравнения с фоном.
    Усредняет несколько последних результатов распознавания и даёт результат на их основании.
    """
    _ACTIVATION_COUNT: int
    _DEACTIVATION_COUNT: int
    _THRESHOLD_SCORE: float
    _LEARNING_RATE: float
    _recognized: bool
    _recognize_counter: int
    _mog2: cv2.BackgroundSubtractorMOG2

    def __init__(
            self,
            background: np.ndarray = None,
            borders: tuple[int, int] = (15, -20),
            learning_rate: float = 1e-4,
            threshold_score: float = 0.65,
            size_multiplier: float = 0.4,
    ):

        self._ACTIVATION_COUNT = max(borders)
        self._DEACTIVATION_COUNT = min(borders)
        self._THRESHOLD_SCORE = threshold_score
        self._LEARNING_RATE = learning_rate
        self._SIZE_MULTIPLIER = size_multiplier

        self._recognized = False
        self._recognize_counter = 0

        self._mog2 = cv2.createBackgroundSubtractorMOG2(detectShadows=True)
        if background is not None:
            self._mog2.apply(background, learningRate=1.0)

    def is_recognized(self, image: np.ndarray) -> bool:
        recognized = self._has_foreground(image)
        if recognized:
            self._recognize_counter = max(self._recognize_counter, 0) + 1
        else:
            self._recognize_counter = min(self._recognize_counter, 0) - 1

        if self._recognize_counter >= self._ACTIVATION_COUNT:
            self._recognized = True
        elif self._recognize_counter <= self._DEACTIVATION_COUNT:
            self._recognized = False

        # нормализация в диапазоне
        self._recognize_counter = max(self._recognize_counter, self._DEACTIVATION_COUNT)
        self._recognize_counter = min(self._recognize_counter, self._ACTIVATION_COUNT)

        return self._recognized

    def _has_foreground(self, image: np.ndarray) -> bool:
        image = self._resize_image(image, self._SIZE_MULTIPLIER)
        learning_rate = self._LEARNING_RATE * (not self._recognized)
        score = get_mog2_foreground_score(self._mog2, image, learning_rate)
        return score > self._THRESHOLD_SCORE

    @staticmethod
    def _resize_image(image: np.ndarray, multiplier: float) -> np.ndarray:
        height = int(multiplier * image.shape[0])
        width = int(multiplier * image.shape[1])
        return cv2.resize(image, (width, height))


class SensorPackRecognizer(BaseRecognizer):
    """
    Определение наличия пачки посредством SNMP-запросов к датчику расстояния
    """
    # TODO: возможно стоит вынести блокирующие запросы в асинхронный процесс
    #  и обеспечить связь данного класса с процессом через очередь для исключения блокировок

    OID = {
        'ALARM-1': '.1.3.6.1.4.1.40418.2.6.2.2.1.3.1.2',
        'ALARM-2': '.1.3.6.1.4.1.40418.2.6.2.2.1.3.1.3',
        'ALARM-3': '.1.3.6.1.4.1.40418.2.6.2.2.1.3.1.4',
        'ALARM-4': '.1.3.6.1.4.1.40418.2.6.2.2.1.3.1.5',
    }

    def __init__(self, *, detector_ip: str):
        # TODO: убрать костанты и сделать нормальную расширяемость
        #  добавить усреднение результата и другие
        self._SKIPFRAME_MOD = 15
        self._skipframe_counter = self._SKIPFRAME_MOD + 1
        self._recognized = False
        self._snmp_detector_ip = detector_ip
        self._snmp_engine = snmp.SnmpEngine()
        self._snmp_community_string = 'public'
        self._snmp_port = 161
        self._snmp_context = snmp.ContextData()

    def is_recognized(self, _: np.ndarray) -> bool:
        self._skipframe_counter = (self._skipframe_counter + 1) % self._SKIPFRAME_MOD
        if self._skipframe_counter == 0:
            self._recognized = self._has_pack()
        return self._recognized

    def _has_pack(self) -> bool:
        erd = self._snmp_get(self.OID['ALARM-3'])
        return erd is not None and int(erd) != 0

    def _snmp_get(self, key: str) -> str:
        """получение состояния"""
        key_object = snmp.ObjectType(snmp.ObjectIdentity(key))
        t = snmp.getCmd(
            self._snmp_engine,
            snmp.CommunityData(self._snmp_community_string),
            snmp.UdpTransportTarget((self._snmp_detector_ip, self._snmp_port)),
            self._snmp_context,
            key_object,
        )
        errorIndication, errorStatus, errorIndex, varBinds = next(t)
        for name, val in varBinds:
            return val.prettyPrint()
