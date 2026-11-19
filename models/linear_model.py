# -*- coding: utf-8 -*-

from __future__ import annotations

import numpy as np
from sklearn.linear_model import LinearRegression

from models.base_model import BaseModel


class LinearModel(BaseModel):
    """线性回归：Tw = a + b * Ta"""

    name = "Linear"

    def __init__(self):
        super().__init__()
        self._model = LinearRegression()

    def fit(self, X: dict, y: np.ndarray, **kwargs) -> "LinearModel":
        ta = np.asarray(X["Ta"], dtype=float).reshape(-1, 1)
        tw = np.asarray(y, dtype=float)
        self._model.fit(ta, tw)
        self._params = {
            "a": float(self._model.intercept_),
            "b": float(self._model.coef_[0]),
        }
        y_pred = self.predict(X)
        self._metrics = self.evaluate(y, y_pred)
        return self

    def predict(self, X: dict) -> np.ndarray:
        ta = np.asarray(X["Ta"], dtype=float).reshape(-1, 1)
        return self._model.predict(ta)
