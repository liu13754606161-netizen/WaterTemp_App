# -*- coding: utf-8 -*-
"""多模型比较：基于已训练 model_results 汇总、可视化与导出。"""

from __future__ import annotations

import os
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

from models.model_catalog import ALL_MODEL_KEYS, MODEL_KEY_TO_LABEL

def build_comparison_from_results(
    model_results: dict[str, dict | None],
    data_dict: dict,
    selected_keys: list[str] | None = None,
) -> dict[str, Any]:
    """从 model_results 构建比较结果（仅汇总已训练模型，不重新训练）。"""
    if selected_keys is None:
        selected_keys = [k for k in ALL_MODEL_KEYS if model_results.get(k, {}) and model_results[k].get("trained")]

    if len(selected_keys) < 2:
        raise ValueError("至少需要选择 2 个已训练的模型进行比较。")

    predictions: dict[str, np.ndarray] = {}
    metrics_rows: list[dict] = []

    for key in selected_keys:
        entry = model_results.get(key)
        if not entry or not entry.get("trained"):
            raise ValueError(f"模型未训练，无法参与比较：{MODEL_KEY_TO_LABEL[key]}")

        label = MODEL_KEY_TO_LABEL[key]
        predictions[label] = np.asarray(entry["Tw_pred"], dtype=float)
        row: dict[str, Any] = {"模型": label, **entry["metrics"]}
        for pname, pval in entry.get("params", {}).items():
            row[f"param_{pname}"] = pval
        metrics_rows.append(row)

    metrics_df = pd.DataFrame(metrics_rows).sort_values("RMSE", ascending=True).reset_index(drop=True)

    return {
        "predictions": predictions,
        "metrics_df": metrics_df,
        "selected_keys": list(selected_keys),
        "y": np.asarray(data_dict["Tw"], dtype=float),
        "dates": data_dict["dates"],
        "model_results": model_results,
    }


def metrics_summary_table(metrics_df: pd.DataFrame) -> pd.DataFrame:
    cols = ["模型", "RMSE", "MAE", "R2", "NSE"]
    out = metrics_df[cols].copy()
    return out.rename(columns={"R2": "R²"})


def export_comparison_csv(result: dict, path: str) -> None:
    metrics_df = result["metrics_df"]
    rows = []
    for _, row in metrics_df.iterrows():
        entry = {
            "模型": row["模型"],
            "RMSE": row["RMSE"],
            "MAE": row["MAE"],
            "R2": row["R2"],
            "NSE": row["NSE"],
        }
        for col in metrics_df.columns:
            if col.startswith("param_"):
                entry[col.replace("param_", "")] = row[col]
        rows.append(entry)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8-sig")


def plot_time_series_comparison(result: dict, ax=None):
    dates = result["dates"]
    y = result["y"]
    preds = result["predictions"]

    if ax is None:
        fig, ax = plt.subplots(figsize=(10, 5))
    else:
        fig = ax.figure

    ax.plot(dates, y, color="#1f77b4", linewidth=2, label="实测")
    palette = ["#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b"]
    for i, name in enumerate(preds.keys()):
        ax.plot(
            dates,
            preds[name],
            linewidth=1.8,
            linestyle="--",
            color=palette[i % len(palette)],
            label=name,
        )

    ax.set_title("多模型水温时间序列对比", fontsize=13, pad=12)
    ax.set_xlabel("日期")
    ax.set_ylabel("水温 (°C)")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m"))
    fig.autofmt_xdate()
    return fig


def plot_scatter_comparison(result: dict, ax=None):
    y = result["y"]
    preds = result["predictions"]

    if ax is None:
        fig, ax = plt.subplots(figsize=(6, 6))
    else:
        fig = ax.figure

    scatter_labels = list(preds.keys())
    markers = ["o", "s", "^", "D", "v", "P"]
    colors = ["#d62728", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf", "#8c564b"]

    all_vals = [y] + [preds[n] for n in scatter_labels]
    lo = float(min(v.min() for v in all_vals))
    hi = float(max(v.max() for v in all_vals))
    pad = (hi - lo) * 0.05 or 1.0
    ax.plot(
        [lo - pad, hi + pad],
        [lo - pad, hi + pad],
        color="#333333",
        linestyle="--",
        linewidth=2,
        label="y = x",
    )

    for name, marker, color in zip(scatter_labels, markers, colors):
        if name not in preds:
            continue
        ax.scatter(
            y,
            preds[name],
            alpha=0.5,
            s=28,
            marker=marker,
            c=color,
            edgecolors="white",
            linewidths=0.4,
            label=name,
        )

    ax.set_title("实测 vs 预测散点图", fontsize=13, pad=12)
    ax.set_xlabel("实测水温 (°C)")
    ax.set_ylabel("预测水温 (°C)")
    ax.set_aspect("equal", adjustable="box")
    ax.legend(loc="best", fontsize=9)
    ax.grid(True, alpha=0.3)
    return fig


def plot_rmse_bar(result: dict, ax=None):
    summary = metrics_summary_table(result["metrics_df"])
    models = summary["模型"].tolist()
    rmse_vals = summary["RMSE"].tolist()

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))
    else:
        fig = ax.figure

    x = np.arange(len(models))
    ax.bar(x, rmse_vals, color="#1a73e8", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("RMSE")
    ax.set_title("RMSE 比较")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def plot_nse_bar(result: dict, ax=None):
    summary = metrics_summary_table(result["metrics_df"])
    models = summary["模型"].tolist()
    nse_vals = summary["NSE"].tolist()

    if ax is None:
        fig, ax = plt.subplots(figsize=(8, 4))
    else:
        fig = ax.figure

    x = np.arange(len(models))
    ax.bar(x, nse_vals, color="#34a853", alpha=0.85)
    ax.set_xticks(x)
    ax.set_xticklabels(models, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("NSE")
    ax.set_title("NSE 比较")
    ax.grid(True, axis="y", alpha=0.3)
    fig.tight_layout()
    return fig


def save_comparison_figures(result: dict, output_dir: str) -> dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)
    paths: dict[str, str] = {}

    fig1, _ = plt.subplots(figsize=(10, 5))
    plot_time_series_comparison(result, ax=fig1.gca())
    fig1.tight_layout()
    p1 = os.path.join(output_dir, "comparison_timeseries.png")
    fig1.savefig(p1, dpi=150, bbox_inches="tight")
    plt.close(fig1)
    paths["timeseries"] = p1

    fig2, _ = plt.subplots(figsize=(6, 6))
    plot_scatter_comparison(result, ax=fig2.gca())
    fig2.tight_layout()
    p2 = os.path.join(output_dir, "comparison_scatter.png")
    fig2.savefig(p2, dpi=150, bbox_inches="tight")
    plt.close(fig2)
    paths["scatter"] = p2

    fig3, _ = plt.subplots(figsize=(8, 4))
    plot_rmse_bar(result, ax=fig3.gca())
    p3 = os.path.join(output_dir, "comparison_rmse.png")
    fig3.savefig(p3, dpi=150, bbox_inches="tight")
    plt.close(fig3)
    paths["rmse"] = p3

    fig4, _ = plt.subplots(figsize=(8, 4))
    plot_nse_bar(result, ax=fig4.gca())
    p4 = os.path.join(output_dir, "comparison_nse.png")
    fig4.savefig(p4, dpi=150, bbox_inches="tight")
    plt.close(fig4)
    paths["nse"] = p4

    return paths
