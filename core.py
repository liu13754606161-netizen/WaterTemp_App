# -*- coding: utf-8 -*-
"""RiverTemp-Reconstructor 共享核心算法（桌面版调用）"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import differential_evolution
from sklearn.metrics import mean_squared_error, r2_score

# 五个模型参数的中文说明（用于表格展示）
PARAM_DEFINITIONS = [
    ("a1", "热平衡常数"),
    ("a2", "气温影响系数"),
    ("a3", "水温衰减系数"),
    ("a4", "季节项幅度"),
    ("a5", "季节项相位（年积日）"),
]


def simulate_air2stream(params, Ta, initial_Tw, doy):
    """Air2Stream 水温模拟：根据气温序列与 5 个参数递推水温。"""
    a1, a2, a3, a4, a5 = params
    Tw_sim = np.zeros(len(Ta))
    Tw_sim[0] = initial_Tw

    for t in range(1, len(Ta)):
        dt_term = a4 * np.cos(2 * np.pi * (doy[t] - a5) / 365.0)
        Tw_sim[t] = Tw_sim[t - 1] + a1 + a2 * Ta[t - 1] - a3 * Tw_sim[t - 1] + dt_term

    return Tw_sim


def objective_function(params, Ta, Tw_obs, doy):
    """差分进化目标函数：最小化 RMSE。"""
    Tw_sim = simulate_air2stream(params, Ta, Tw_obs.iloc[0], doy)
    return np.sqrt(mean_squared_error(Tw_obs, Tw_sim))


def calibrate_model(Ta, Tw_obs, doy, popsize=15, maxiter=100, tol=0.01):
    """调用差分进化算法率定 5 个参数。"""
    bounds = [(-20, 20), (1e-6, 2), (0, 1), (-20, 20), (0, 365)]
    return differential_evolution(
        objective_function,
        bounds,
        args=(Ta, Tw_obs, doy),
        popsize=popsize,
        maxiter=maxiter,
        tol=tol,
        polish=True,
    )


def calculate_performance_metrics(Tw_obs, Tw_sim):
    """计算 RMSE、NSE、R²、MAE。"""
    tw_obs = np.asarray(Tw_obs)
    tw_sim = np.asarray(Tw_sim)
    rmse = np.sqrt(mean_squared_error(tw_obs, tw_sim))
    denom = np.sum((tw_obs - np.mean(tw_obs)) ** 2)
    nse = 1 - (np.sum((tw_obs - tw_sim) ** 2) / denom) if denom > 0 else float("nan")
    return {
        "RMSE": rmse,
        "NSE": nse,
        "R2": r2_score(tw_obs, tw_sim),
        "MAE": np.mean(np.abs(tw_obs - tw_sim)),
    }


def prepare_series(df: pd.DataFrame, date_col: str, ta_col: str, tw_col: str) -> dict:
    """根据用户选择的列名，清洗并返回率定所需序列。"""
    if len({date_col, ta_col, tw_col}) != 3:
        raise ValueError("日期、气温、水温必须映射到三列不同的字段。")

    work = df.copy()
    dates = pd.to_datetime(work[date_col], errors="coerce")
    ta = pd.to_numeric(work[ta_col], errors="coerce")
    tw = pd.to_numeric(work[tw_col], errors="coerce")

    valid = dates.notna() & ta.notna() & tw.notna()
    if valid.sum() < 10:
        raise ValueError("有效数据不足（至少需要 10 条无缺失记录）。")

    dates = dates[valid].reset_index(drop=True)
    ta = ta[valid].reset_index(drop=True)
    tw = tw[valid].reset_index(drop=True)
    doy = dates.dt.dayofyear.to_numpy()

    return {
        "dates": dates,
        "Ta": ta.to_numpy(dtype=float),
        "Tw": tw.to_numpy(dtype=float),
        "doy": doy,
    }


def run_calibration(data_dict: dict, popsize=15, maxiter=100, tol=0.01) -> dict:
    """执行完整率定流程，返回参数、指标与模拟序列。"""
    ta = data_dict["Ta"]
    tw = data_dict["Tw"]
    doy = data_dict["doy"]
    tw_series = pd.Series(tw)

    result = calibrate_model(ta, tw_series, doy, popsize=popsize, maxiter=maxiter, tol=tol)
    best_params = result.x
    tw_sim = simulate_air2stream(best_params, ta, tw[0], doy)
    metrics = calculate_performance_metrics(tw, tw_sim)

    return {
        "params": best_params,
        "metrics": metrics,
        "Tw_sim": tw_sim,
        "optimization": result,
    }


def params_to_dataframe(params) -> pd.DataFrame:
    """将 5 个参数转为带中文说明的表格。"""
    rows = []
    for i, (name, desc) in enumerate(PARAM_DEFINITIONS):
        rows.append({"参数": name, "数值": float(params[i]), "物理含义": desc})
    return pd.DataFrame(rows)


def results_to_dataframe(data_dict: dict, calibration: dict) -> pd.DataFrame:
    """导出用结果表。"""
    tw_sim = calibration["Tw_sim"]
    tw_obs = data_dict["Tw"]
    return pd.DataFrame(
        {
            "Date": data_dict["dates"].dt.strftime("%Y-%m-%d"),
            "Observed_Tw": tw_obs,
            "Simulated_Tw": tw_sim,
            "Residual": tw_sim - tw_obs,
        }
    )
