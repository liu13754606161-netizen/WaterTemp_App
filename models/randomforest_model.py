# -*- coding: utf-8 -*-

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from models.base_model import BaseModel


class RandomForestModel(BaseModel):
    """随机森林：特征 Ta、month、dayofyear。"""

    name = "Random Forest"

    def __init__(self):
        super().__init__()
        self._model = RandomForestRegressor(
            n_estimators=200,
            max_depth=10,
            random_state=42,
        )

    @staticmethod
    def _build_features(X: dict) -> np.ndarray:
        dates = pd.to_datetime(X["dates"])
        ta = np.asarray(X["Ta"], dtype=float)
        month = dates.dt.month.to_numpy(dtype=float)
        doy = dates.dt.dayofyear.to_numpy(dtype=float)
        return np.column_stack([ta, month, doy])

    def fit(self, X: dict, y: np.ndarray, **kwargs) -> "RandomForestModel":
        features = self._build_features(X)
        tw = np.asarray(y, dtype=float)
        self._model.fit(features, tw)
        self._params = {
            "n_estimators": 200,
            "max_depth": 10,
            "random_state": 42,
        }
        y_pred = self.predict(X)
        self._metrics = self.evaluate(y, y_pred)
        return self

    def predict(self, X: dict) -> np.ndarray:
        return self._model.predict(self._build_features(X))
