# -*- coding: utf-8 -*-

from __future__ import annotations

from abc import ABC, abstractmethod

import numpy as np

from metrics import evaluate_all


class BaseModel(ABC):
    """所有水温模型的统一接口。"""

    name: str = "BaseModel"

    def __init__(self):
        self._params: dict | None = None
        self._metrics: dict[str, float] | None = None

    @abstractmethod
    def fit(self, X: dict, y: np.ndarray, **kwargs) -> "BaseModel":
        pass

    @abstractmethod
    def predict(self, X: dict) -> np.ndarray:
        pass

    def evaluate(self, y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
        return evaluate_all(y_true, y_pred)

    @property
    def params(self) -> dict:
        return self._params or {}

    @property
    def metrics(self) -> dict[str, float]:
        return self._metrics or {}

    def get_params_dict(self) -> dict[str, float]:
        return dict(self.params)
