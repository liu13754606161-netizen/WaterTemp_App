# -*- coding: utf-8 -*-

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression

from models.base_model import BaseModel


class TeqModel(BaseModel):
    """平衡温度模型 Teq-2：Tw = e1 + e2 * Ta，预测值截断至 >= 0 ℃。"""

    name = "Teq"

    def __init__(self):
        super().__init__()
        self._model = LinearRegression()

    def fit(self, X: dict, y: np.ndarray, **kwargs) -> "TeqModel":
        ta = np.asarray(X["Ta"], dtype=float).reshape(-1, 1)
        tw = np.asarray(y, dtype=float)
        self._model.fit(ta, tw)
        self._params = {
            "e1": float(self._model.intercept_),
            "e2": float(self._model.coef_[0]),
        }
        y_pred = self.predict(X)
        self._metrics = self.evaluate(y, y_pred)
        return self

    def predict(self, X: dict) -> np.ndarray:
        ta = np.asarray(X["Ta"], dtype=float)
        pred = self._params["e1"] + self._params["e2"] * ta
        return np.maximum(pred, 0.0)
