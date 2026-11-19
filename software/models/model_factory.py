# -*- coding: utf-8 -*-

from __future__ import annotations

from models.air2stream_model import Air2StreamModel
from models.base_model import BaseModel
from models.linear_model import LinearModel
from models.randomforest_model import RandomForestModel
from models.seasonal_linear_model import SeasonalLinearModel
from models.teq_model import TeqModel

from models.model_catalog import ALL_MODEL_KEYS

MODEL_NAMES = ALL_MODEL_KEYS

_MODEL_MAP = {
    "Air2Stream": Air2StreamModel,
    "Linear": LinearModel,
    "Seasonal Linear": SeasonalLinearModel,
    "Teq": TeqModel,
    "Random Forest": RandomForestModel,
}


def create_model(name: str, **kwargs) -> BaseModel:
    if name not in _MODEL_MAP:
        raise ValueError(f"未知模型：{name}")
    return _MODEL_MAP[name](**kwargs)
