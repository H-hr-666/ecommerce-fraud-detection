"""
数据服务模块
负责数据集加载、清洗、描述性统计
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import os
import logging

from config import DATASET_PATH, RAW_COLUMNS

logger = logging.getLogger(__name__)


def generate_sample_dataset(n_samples: int = 38662) -> pd.DataFrame:
    """
    生成模拟电商交易数据集（当Kaggle数据集不可用时）

    Args:
        n_samples: 样本数量，默认38662（与论文一致）

    Returns:
        模拟的电商交易DataFrame
    """
    np.random.seed(42)

    # 正常交易样本（约95%）
    n_normal = int(n_samples * 0.95)
    # 刷单样本（约5%）
    n_fraud = n_samples - n_normal

    # 正常交易特征
    normal_data = {
        "user_id": [f"U{str(i).zfill(6)}" for i in range(n_normal)],
        "order_id": [f"O{str(i).zfill(8)}" for i in range(n_normal)],
        "amount": np.random.lognormal(mean=4.5, sigma=1.2, size=n_normal).clip(1, 10000),
        "time_diff": np.random.exponential(scale=90, size=n_normal).clip(5, 3600),
        "order_time": np.random.choice(range(8, 24), size=n_normal),  # 8-23点为主
        "device_type": np.random.choice(["iOS", "Android", "PC", "H5"],
                                        size=n_normal, p=[0.35, 0.4, 0.15, 0.1])
    }

    # 刷单交易特征（机器脚本特征）
    fraud_data = {
        "user_id": [f"U{str(i).zfill(6)}" for i in range(n_normal, n_normal + n_fraud)],
        "order_id": [f"O{str(i).zfill(8)}" for i in range(n_normal, n_normal + n_fraud)],
        "amount": np.random.choice([9.9, 19.9, 29.9, 4.9], size=n_fraud),  # 低价商品为主
        "time_diff": np.random.exponential(scale=5, size=n_fraud).clip(1, 30),  # 极短间隔
        "order_time": np.random.choice(range(1, 7), size=n_fraud),  # 凌晨1-6点
        "device_type": np.random.choice(["Android", "iOS"], size=n_fraud, p=[0.7, 0.3])  # 设备集中
    }

    # 合并数据
    df = pd.concat([
        pd.DataFrame(normal_data),
        pd.DataFrame(fraud_data)
    ], ignore_index=True)

    # 随机打乱
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    # 添加少量缺失值（模拟真实数据）
    missing_idx = np.random.choice(n_samples, size=int(n_samples * 0.02), replace=False)
    df.loc[missing_idx[:len(missing_idx)//2], "amount"] = np.nan
    df.loc[missing_idx[len(missing_idx)//2:], "time_diff"] = np.nan

    return df


def load_dataset(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    加载数据集

    Args:
        file_path: 数据集文件路径，为None时使用默认路径

    Returns:
        加载的DataFrame
    """
    if file_path is None:
        file_path = DATASET_PATH

    if os.path.exists(file_path):
        logger.info(f"从文件加载数据集: {file_path}")
        df = pd.read_csv(file_path)
    else:
        logger.warning(f"数据集文件不存在: {file_path}，生成模拟数据集")
        df = generate_sample_dataset()
        # 保存生成的数据集
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_csv(file_path, index=False)

    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    数据清洗：删除关键字段缺失的记录

    Args:
        df: 原始数据

    Returns:
        清洗后的数据
    """
    original_count = len(df)

    # 删除amount和time_diff缺失的行
    df_cleaned = df.dropna(subset=["amount", "time_diff"])

    cleaned_count = len(df_cleaned)
    removed_count = original_count - cleaned_count

    logger.info(f"数据清洗完成: 原始{original_count}条, 删除{removed_count}条缺失记录, 剩余{cleaned_count}条")

    return df_cleaned


def get_descriptive_stats(df: pd.DataFrame) -> Dict:
    """
    计算描述性统计（对标论文表3-1）

    Args:
        df: 清洗后的数据

    Returns:
        描述性统计字典
    """
    stats = {
        "sample_count": len(df),
        "amount": {
            "mean": round(float(df["amount"].mean()), 2),
            "std": round(float(df["amount"].std()), 2),
            "min": round(float(df["amount"].min()), 2),
            "max": round(float(df["amount"].max()), 2),
            "median": round(float(df["amount"].median()), 2)
        },
        "time_diff": {
            "mean": round(float(df["time_diff"].mean()), 2),
            "std": round(float(df["time_diff"].std()), 2),
            "min": round(float(df["time_diff"].min()), 2),
            "max": round(float(df["time_diff"].max()), 2),
            "median": round(float(df["time_diff"].median()), 2)
        },
        "rush_hour_ratio": round(float((df["order_time"].between(1, 6)).mean()), 4),
        "device_distribution": df["device_type"].value_counts().to_dict()
    }

    return stats


def get_raw_data_info(df: pd.DataFrame) -> Dict:
    """
    获取原始数据基本信息

    Args:
        df: 原始数据

    Returns:
        数据信息字典
    """
    return {
        "total_orders": len(df),
        "columns": list(df.columns),
        "missing_values": df.isnull().sum().to_dict(),
        "data_types": df.dtypes.astype(str).to_dict()
    }
