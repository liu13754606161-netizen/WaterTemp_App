# -*- coding: utf-8 -*-

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from models.base_model import BaseModel


class SeasonalLinearModel(BaseModel):
    """季节线性回归：1–6 月与 7–12 月分别拟合 Tw = a + b * Ta。"""

    name = "Seasonal Linear"

    def __init__(self):
        super().__init__()
        self._model_a = LinearRegression()
        self._model_b = LinearRegression()

    def fit(self, X: dict, y: np.ndarray, **kwargs) -> "SeasonalLinearModel":
        dates = pd.to_datetime(X["dates"])
        ta = np.asarray(X["Ta"], dtype=float)
        tw = np.asarray(y, dtype=float)
        month = dates.dt.month.to_numpy()

        mask_a = month <= 6
        mask_b = month > 6

        if mask_a.sum() < 2 or mask_b.sum() < 2:
            raise ValueError("季节线性回归需要 1–6 月与 7–12 月均至少有 2 条有效记录。")

        self._model_a.fit(ta[mask_a].reshape(-1, 1), tw[mask_a])
        self._model_b.fit(ta[mask_b].reshape(-1, 1), tw[mask_b])

        self._params = {
            "a1": float(self._model_a.intercept_),
            "b1": float(self._model_a.coef_[0]),
            "a2": float(self._model_b.intercept_),
            "b2": float(self._model_b.coef_[0]),
        }
        y_pred = self.predict(X)
        self._metrics = self.evaluate(y, y_pred)
        return self

    def predict(self, X: dict) -> np.ndarray:
        dates = pd.to_datetime(X["dates"])
        ta = np.asarray(X["Ta"], dtype=float)
        month = dates.dt.month.to_numpy()
        pred = np.zeros(len(ta), dtype=float)

        mask_a = month <= 6
        mask_b = ~mask_a

        if mask_a.any():
            pred[mask_a] = self._model_a.predict(ta[mask_a].reshape(-1, 1))
        if mask_b.any():
            pred[mask_b] = self._model_b.predict(ta[mask_b].reshape(-1, 1))
        return pred
