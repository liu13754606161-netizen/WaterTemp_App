# -*- coding: utf-8 -*-
"""统一评价指标模块。"""

from __future__ import annotations

import numpy as np
from sklearn.metrics import mean_squared_error, r2_score


def rmse(obs: np.ndarray, pred: np.ndarray) -> float:
    obs = np.asarray(obs, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return float(np.sqrt(np.mean((obs - pred) ** 2)))


def mae(obs: np.ndarray, pred: np.ndarray) -> float:
    obs = np.asarray(obs, dtype=float)
    pred = np.asarray(pred, dtype=float)
    return float(np.mean(np.abs(obs - pred)))


def r2(obs: np.ndarray, pred: np.ndarray) -> float:
    return float(r2_score(obs, pred))


def nse(obs: np.ndarray, pred: np.ndarray) -> float:
    obs = np.asarray(obs, dtype=float)
    pred = np.asarray(pred, dtype=float)
    denominator = np.sum((obs - np.mean(obs)) ** 2)
    if denominator == 0:
        return float("nan")
    return float(1 - np.sum((obs - pred) ** 2) / denominator)


def evaluate_all(obs: np.ndarray, pred: np.ndarray) -> dict[str, float]:
    return {
        "RMSE": rmse(obs, pred),
        "MAE": mae(obs, pred),
        "R2": r2(obs, pred),
        "NSE": nse(obs, pred),
    }
