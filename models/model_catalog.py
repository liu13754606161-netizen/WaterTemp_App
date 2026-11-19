# -*- coding: utf-8 -*-
"""模型展示信息：公式、参数说明、训练方法（与 core 计算逻辑解耦）。"""

from __future__ import annotations

# 下拉框显示名 -> 内部键
MODEL_LABEL_TO_KEY: dict[str, str] = {
    "Air2Stream": "Air2Stream",
    "Linear Regression": "Linear",
    "Seasonal Linear": "Seasonal Linear",
    "Teq": "Teq",
    "Random Forest": "Random Forest",
}

MODEL_KEY_TO_LABEL: dict[str, str] = {v: k for k, v in MODEL_LABEL_TO_KEY.items()}

ALL_MODEL_KEYS: list[str] = list(MODEL_KEY_TO_LABEL.keys())
GUI_MODEL_LABELS: list[str] = list(MODEL_LABEL_TO_KEY.keys())


def _entry(
    title: str,
    latex: str | None,
    plain_formula: str | None,
    params: list[tuple[str, str, str, str]],
    description: str,
    method: str,
    show_formula: bool = True,
) -> dict:
    return {
        "title": title,
        "latex": latex,
        "plain_formula": plain_formula,
        "params": params,
        "description": description,
        "method": method,
        "show_formula": show_formula,
    }


MODEL_CATALOG: dict[str, dict] = {
    "Air2Stream": _entry(
        title="Air2Stream河流水温模型",
        latex=(
            r"$T_w(t)=T_w(t-1)+a_1+a_2\,T_a(t-1)-a_3\,T_w(t-1)"
            r"+a_4\cos\!\left(\dfrac{2\pi(\mathrm{doy}-a_5)}{365}\right)$"
        ),
        plain_formula=None,
        params=[
            ("a1", "热输入基准项", "℃/day", "[-20, 20]"),
            ("a2", "气温影响系数", "无量纲", "[1e-6, 2]"),
            ("a3", "热耗散系数", "day⁻¹", "[0, 1]"),
            ("a4", "季节振幅参数", "℃", "[-20, 20]"),
            ("a5", "季节相位参数（年积日）", "day", "[0, 365]"),
        ],
        description="基于热平衡方程和随机参数率定方法建立的混合模型。",
        method="差分进化算法（Differential Evolution）",
    ),
    "Linear": _entry(
        title="线性回归模型",
        latex=r"$T_w = a + b\,T_a$",
        plain_formula=None,
        params=[
            ("a", "截距", "℃", "—"),
            ("b", "气温敏感系数", "℃/℃", "—"),
        ],
        description="最简单线性关系模型。",
        method="LinearRegression",
    ),
    "Seasonal Linear": _entry(
        title="季节线性回归模型",
        latex=(
            r"1–6月：$T_w=a_1+b_1 T_a$" "\n"
            r"7–12月：$T_w=a_2+b_2 T_a$"
        ),
        plain_formula="1–6月: Tw = a1 + b1·Ta\n7–12月: Tw = a2 + b2·Ta",
        params=[
            ("a1", "前半年截距", "℃", "—"),
            ("b1", "前半年气温系数", "℃/℃", "—"),
            ("a2", "后半年截距", "℃", "—"),
            ("b2", "后半年气温系数", "℃/℃", "—"),
        ],
        description="考虑季节差异的分段线性模型。",
        method="两次 LinearRegression",
    ),
    "Teq": _entry(
        title="平衡温度模型 Teq-2",
        latex=r"$T_w=\max(e_1+e_2\,T_a,\;0)$",
        plain_formula=None,
        params=[
            ("e1", "平衡温度基准值", "℃", "—"),
            ("e2", "气温响应系数", "℃/℃", "—"),
        ],
        description="平衡温度形式，预测水温不低于 0 ℃。",
        method="LinearRegression + 物理约束截断",
    ),
    "Random Forest": _entry(
        title="Random Forest 回归模型",
        latex=None,
        plain_formula=None,
        params=[
            ("n_estimators", "决策树数量", "—", "200"),
            ("max_depth", "最大树深", "—", "10"),
            ("random_state", "随机种子", "—", "42"),
        ],
        description="基于集成树模型进行非线性预测。",
        method="RandomForestRegressor",
        show_formula=False,
    ),
}


def get_model_key(label: str) -> str:
    if label not in MODEL_LABEL_TO_KEY:
        raise ValueError(f"未知模型：{label}")
    return MODEL_LABEL_TO_KEY[label]


def get_catalog(key: str) -> dict:
    return MODEL_CATALOG[key]
