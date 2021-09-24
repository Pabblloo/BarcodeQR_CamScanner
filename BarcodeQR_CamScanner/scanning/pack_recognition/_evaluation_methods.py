"""
Различные метрики для определения и аппроксимации всего, что может происходить на камерах.
"""
from functools import reduce
from typing import Any

import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from tensorflow.lite.python.interpreter import Interpreter

from ..image_utils import get_normalized_sum


def get_neuronet_score(interpreter: Interpreter, image: np.ndarray) -> float:
    """
    Оценка наличия пачки на изображении, полученная от нейросети

    **Осторожно: очень долго (200мс/кадр) работает!**

    Args:
        interpreter: интерпретатор с уже загруженной и обученной нейросетью
        image: изображение, которое нужно проверить

    Returns:
        показатель движения на изображении
            0.0 (движения нет) до 1.0 (на изображении двигаются все пиксели)
    """
    input_detail: dict[str, Any] = interpreter.get_input_details()[0]
    output_detail: dict[str, Any] = interpreter.get_output_details()[0]

    input_size = tuple(input_detail['shape'][[2, 1]])

    image = cv2.resize(image, input_size)
    cv2.cvtColor(image, cv2.COLOR_BGR2RGB, image)

    input_layer = np.expand_dims(image, axis=0)
    input_layer = input_layer.astype('float32') * (1 / 255)

    interpreter.set_tensor(input_detail['index'], input_layer)
    interpreter.invoke()

    predict_value = interpreter.get_tensor(output_detail['index'])[0][0]
    return predict_value


def get_absdiff_motion_score(img1: np.ndarray, img2: np.ndarray, img3: np.ndarray) -> float:
    """
    Вычисление показателя движения (от 0.0 до 1.0) между 3-мя изображениями.

    Для корректного результата изображения должны идти в хронологическом порядке.

    Args:
        3 grayscaled-изображения идентичного размера

    Returns:
        показатель движения на изображении
            от 0.0 (движения нет) до 1.0 (двигается всё)
    """
    diff12 = cv2.absdiff(img1, img2)
    diff23 = cv2.absdiff(img2, img3)
    diff_intersection = cv2.bitwise_and(diff12, diff23, dst=diff23)
    cv2.threshold(diff_intersection, 5, 1, cv2.THRESH_BINARY, dst=diff_intersection)
    score = get_normalized_sum(diff_intersection)
    return score


def get_reverse_ssim_score(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Вычисление показателя НЕсхожести изображений
    через ``scimage.metrics.structural_similarity``

    **Осторожно: очень долго (200мс/кадр) работает!**

    Args:
        2 изображения идентичного размера с эквивалентным кол-вом цветов

    Returns:
        показатель несхожести двух изображений
            от 0.0 (идентичны) до 1.0 (полностью несхожи)
    """
    score = ssim(img1, img2)
    return 1.0 - score


def get_pixelwise_diff_score(img1: np.ndarray, img2: np.ndarray) -> float:
    """
    Вычисление показателя различности изображений
    через суммирование (по модулю) попиксельной разницы

    Args:
        2 изображения идентичного размера с эквивалентным кол-вом цветов

    Returns:
        показатель различия двух изображений
            от 0.0 (идентичны) до 1.0 (полностью различны)
    """
    color_normalizer = 1 / 255
    diff_sum = np.sum(np.abs(img1 - img2.astype('int32')) * color_normalizer)
    pix_count = reduce(lambda x, y: x * y, img1.shape)
    score = diff_sum / pix_count
    return score


def get_mog2_foreground_score(
        mog2: cv2.BackgroundSubtractorMOG2,
        image: np.ndarray,
        learning_rate: float
) -> float:
    """
    Вычисление показателя различности изображения с фоном.

    Args:
        mog2: объект созданный с помощью cv2.createBackgroundSubtractorMOG2
        image: изображение для оценки схожести с фоном из mog2
        learning_rate: коэффициент переобучения
                       (при 1.0 текущий фон полностью перезапишется, при 0.0 - не изменится)

    Returns:
        показатель различия текущего изображения от уже имеющегося в mog2 фона
    """
    mask = mog2.apply(image, learningRate=learning_rate)
    # удаление серых теней
    mask = cv2.threshold(mask, 254, 255, cv2.THRESH_BINARY)[1]
    score = get_normalized_sum(mask)
    return score
