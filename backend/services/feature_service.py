"""
特征工程模块
负责特征构造、标准化处理（严格按论文实现）
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict
from sklearn.preprocessing import StandardScaler
import joblib
import os
import logging

from config import FEATURE_COLUMNS, MODEL_DIR

logger = logging.getLogger(__name__)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    特征工程（严格按论文2.5节实现）

    构造4个建模特征：
    1. log_amount: 交易金额对数化 log(amount+1)
    2. time_diff: 下单时间间隔（秒）
    3. is_rush_hour: 凌晨1-6点标记
    4. device_type: 设备类型编码

    Args:
        df: 清洗后的原始数据

    Returns:
        包含特征的DataFrame
    """
    df_features = df.copy()

    # 1. 交易金额对数化（消除长尾分布）
    df_features["log_amount"] = np.log1p(df_features["amount"])

    # 2. 提取小时，构造凌晨标记（1-6点）
    df_features["is_rush_hour"] = df_features["order_time"].apply(
        lambda x: 1 if 1 <= x <= 6 else 0
    )

    # 3. 设备类型编码
    device_mapping = {"iOS": 0, "Android": 1, "PC": 2, "H5": 3}
    df_features["device_type"] = df_features["device_type"].map(device_mapping).fillna(1)

    # 保留建模特征
    df_model = df_features[FEATURE_COLUMNS].copy()

    logger.info(f"特征工程完成，特征列: {FEATURE_COLUMNS}")

    return df_model


def standardize_features(df_features: pd.DataFrame,
                         scaler: StandardScaler = None,
                         fit: bool = True) -> Tuple[np.ndarray, StandardScaler]:
    """
    Z-Score标准化（论文2.5节）

    将所有特征转化为均值为0，方差为1的标准分布

    Args:
        df_features: 特征DataFrame
        scaler: 已有的标准化器，为None时创建新的
        fit: 是否拟合标准化器

    Returns:
        标准化后的特征矩阵和标准化器
    """
    if scaler is None:
        scaler = StandardScaler()

    if fit:
        X_scaled = scaler.fit_transform(df_features)
        logger.info("标准化器已拟合并转换数据")
    else:
        X_scaled = scaler.transform(df_features)
        logger.info("使用已有标准化器转换数据")

    return X_scaled, scaler


def save_scaler(scaler: StandardScaler, filename: str = "scaler.pkl") -> str:
    """
    保存标准化器到本地

    Args:
        scaler: 标准化器对象
        filename: 保存文件名

    Returns:
        保存路径
    """
    os.makedirs(MODEL_DIR, exist_ok=True)
    filepath = os.path.join(MODEL_DIR, filename)
    joblib.dump(scaler, filepath)
    logger.info(f"标准化器已保存: {filepath}")
    return filepath


def load_scaler(filename: str = "scaler.pkl") -> StandardScaler:
    """
    加载本地标准化器

    Args:
        filename: 文件名

    Returns:
        标准化器对象
    """
    filepath = os.path.join(MODEL_DIR, filename)
    if os.path.exists(filepath):
        scaler = joblib.load(filepath)
        logger.info(f"标准化器已加载: {filepath}")
        return scaler
    else:
        logger.warning(f"标准化器文件不存在: {filepath}")
        return None


def get_feature_stats(X: np.ndarray) -> Dict:
    """
    获取标准化后特征的统计信息

    Args:
        X: 标准化后的特征矩阵

    Returns:
        特征统计字典
    """
    stats = {}
    for i, col in enumerate(FEATURE_COLUMNS):
        stats[col] = {
            "mean": round(float(X[:, i].mean()), 4),
            "std": round(float(X[:, i].std()), 4),
            "min": round(float(X[:, i].min()), 4),
            "max": round(float(X[:, i].max()), 4)
        }
    return stats
