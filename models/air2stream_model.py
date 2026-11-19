# -*- coding: utf-8 -*-

from __future__ import annotations

import numpy as np

from core import run_calibration, simulate_air2stream
from models.base_model import BaseModel


class Air2StreamModel(BaseModel):
    """Air2Stream 模型封装，复用 core.run_calibration，不修改原有率定逻辑。"""

    name = "Air2Stream"

    def __init__(self, popsize: int = 15, maxiter: int = 100, tol: float = 0.01):
        super().__init__()
        self.popsize = popsize
        self.maxiter = maxiter
        self.tol = tol
        self._calibration: dict | None = None
        self._data_dict: dict | None = None

    def fit(self, X: dict, y: np.ndarray, **kwargs) -> "Air2StreamModel":
        data_dict = {
            "dates": X["dates"],
            "Ta": np.asarray(X["Ta"], dtype=float),
            "Tw": np.asarray(y, dtype=float),
            "doy": np.asarray(X["doy"], dtype=float),
        }
        self._data_dict = data_dict
        popsize = kwargs.get("popsize", self.popsize)
        maxiter = kwargs.get("maxiter", self.maxiter)
        tol = kwargs.get("tol", self.tol)

        self._calibration = run_calibration(
            data_dict,
            popsize=popsize,
            maxiter=maxiter,
            tol=tol,
        )
        best = self._calibration["params"]
        self._params = {
            "a1": float(best[0]),
            "a2": float(best[1]),
            "a3": float(best[2]),
            "a4": float(best[3]),
            "a5": float(best[4]),
        }
        y_pred = self.predict(X)
        self._metrics = self.evaluate(y, y_pred)
        return self

    def predict(self, X: dict) -> np.ndarray:
        if self._calibration is None:
            raise RuntimeError("模型尚未训练，请先调用 fit。")
        ta = np.asarray(X["Ta"], dtype=float)
        doy = np.asarray(X["doy"], dtype=float)
        tw = np.asarray(X.get("Tw", self._data_dict["Tw"]), dtype=float)
        params = np.array(
            [
                self._params["a1"],
                self._params["a2"],
                self._params["a3"],
                self._params["a4"],
                self._params["a5"],
            ]
        )
        return simulate_air2stream(params, ta, tw[0], doy)
