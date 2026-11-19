# -*- coding: utf-8 -*-
"""单模型训练与 model_results 状态管理。"""

from __future__ import annotations

import time
from typing import Any

import numpy as np

from core import params_to_dataframe, run_calibration
import pandas as pd

from models.model_catalog import ALL_MODEL_KEYS, MODEL_KEY_TO_LABEL
from models.model_factory import create_model


def build_feature_dict(data_dict: dict) -> dict:
    dates = data_dict["dates"]
    return {
        "dates": dates,
        "Ta": data_dict["Ta"],
        "doy": data_dict["doy"],
        "Tw": data_dict["Tw"],
        "month": pd.to_datetime(dates).dt.month.to_numpy(),
    }


def empty_model_results() -> dict[str, dict | None]:
    return {key: None for key in ALL_MODEL_KEYS}


def is_trained(model_results: dict[str, dict | None], key: str) -> bool:
    entry = model_results.get(key)
    return entry is not None and entry.get("trained", False)


def trained_model_keys(model_results: dict[str, dict | None]) -> list[str]:
    return [k for k in ALL_MODEL_KEYS if is_trained(model_results, k)]


def count_trained(model_results: dict[str, dict | None]) -> int:
    return len(trained_model_keys(model_results))


def all_models_trained(model_results: dict[str, dict | None]) -> bool:
    return count_trained(model_results) == len(ALL_MODEL_KEYS)


def train_model(
    model_key: str,
    data_dict: dict,
    *,
    popsize: int = 15,
    maxiter: int = 100,
    tol: float = 0.01,
) -> dict[str, Any]:
    """训练单个模型，返回 model_results 条目。"""
    t0 = time.perf_counter()
    X = build_feature_dict(data_dict)
    y = np.asarray(data_dict["Tw"], dtype=float)

    if model_key == "Air2Stream":
        cal = run_calibration(data_dict, popsize=popsize, maxiter=maxiter, tol=tol)
        elapsed = time.perf_counter() - t0
        params_df = params_to_dataframe(cal["params"])
        params_dict = {row["参数"]: float(row["数值"]) for _, row in params_df.iterrows()}
        return {
            "model_key": model_key,
            "trained": True,
            "params": params_dict,
            "params_array": cal["params"],
            "metrics": cal["metrics"],
            "Tw_pred": cal["Tw_sim"],
            "calibration_result": cal,
            "elapsed_sec": elapsed,
        }

    kwargs = {}
    if model_key == "Air2Stream":
        model = create_model(model_key, popsize=popsize, maxiter=maxiter, tol=tol)
        kwargs = {"popsize": popsize, "maxiter": maxiter, "tol": tol}
    else:
        model = create_model(model_key)

    model.fit(X, y, **kwargs)
    y_pred = model.predict(X)
    elapsed = time.perf_counter() - t0

    return {
        "model_key": model_key,
        "trained": True,
        "params": model.get_params_dict(),
        "metrics": model.metrics,
        "Tw_pred": y_pred,
        "calibration_result": None,
        "elapsed_sec": elapsed,
    }
