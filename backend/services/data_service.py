"""
数据服务模块
负责数据集加载、清洗、描述性统计
支持 MySQL、CSV 两种数据源
"""

import pandas as pd
import numpy as np
from typing import Optional, Dict, List
import os
import logging

from config import DATASET_PATH, RAW_COLUMNS, MYSQL_CONFIG

logger = logging.getLogger(__name__)


def load_from_mysql() -> pd.DataFrame:
    """
    从本地 MySQL 数据库加载电商交易数据

    Returns:
        从 ecommerce_fraud.transactions 表加载的 DataFrame
    """
    import pymysql

    conn = pymysql.connect(
        host=MYSQL_CONFIG["host"],
        port=MYSQL_CONFIG["port"],
        user=MYSQL_CONFIG["user"],
        password=MYSQL_CONFIG["password"],
        database=MYSQL_CONFIG["database"],
        charset="utf8mb4"
    )

    query = f"SELECT user_id, order_id, amount, time_diff, order_time, device_type, is_cheat FROM {MYSQL_CONFIG['table']}"
    df = pd.read_sql(query, conn)
    conn.close()

    logger.info(f"从 MySQL 加载 {len(df)} 条数据（{MYSQL_CONFIG['host']}:{MYSQL_CONFIG['port']}/{MYSQL_CONFIG['database']}.{MYSQL_CONFIG['table']}）")
    return df


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

    # 添加 is_cheat 标签列（0=正常，1=刷单）
    df["is_cheat"] = 0
    df.loc[n_normal:, "is_cheat"] = 1

    # 添加少量缺失值（模拟真实数据）
    missing_idx = np.random.choice(n_samples, size=int(n_samples * 0.02), replace=False)
    df.loc[missing_idx[:len(missing_idx)//2], "amount"] = np.nan
    df.loc[missing_idx[len(missing_idx)//2:], "time_diff"] = np.nan

    return df


def load_dataset(file_path: Optional[str] = None) -> pd.DataFrame:
    """
    加载数据集（优先从 MySQL，回退到 CSV）

    Args:
        file_path: 数据集文件路径，为None时使用默认路径

    Returns:
        加载的DataFrame
    """
    # 1. 优先从 MySQL 读取
    try:
        df = load_from_mysql()
        if len(df) > 0:
            return df
    except Exception as e:
        logger.warning(f"MySQL 读取失败，回退到 CSV: {e}")

    # 2. 回退到 CSV 文件
    if file_path is None:
        file_path = DATASET_PATH

    if os.path.exists(file_path):
        logger.info(f"从文件加载数据集: {file_path}")
        df = pd.read_csv(file_path)
    else:
        logger.warning(f"数据集文件不存在: {file_path}，生成模拟数据集")
        df = generate_sample_dataset()
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        df.to_csv(file_path, index=False)

    return df


def clean_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    数据清洗：删除关键字段缺失的记录，保留 is_cheat 标签列

    Args:
        df: 原始数据

    Returns:
        清洗后的数据
    """
    original_count = len(df)

    # 删除amount和time_diff缺失的行
    df_cleaned = df.dropna(subset=["amount", "time_diff"])

    # 确保 is_cheat 列存在且为整数类型
    if "is_cheat" in df_cleaned.columns:
        df_cleaned["is_cheat"] = df_cleaned["is_cheat"].fillna(0).astype(int)
    else:
        df_cleaned["is_cheat"] = 0

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

    # 真实标签统计（is_cheat 列）
    if "is_cheat" in df.columns:
        cheat_count = int(df["is_cheat"].sum())
        stats["labeled_fraud_count"] = cheat_count
        stats["labeled_fraud_ratio"] = round(cheat_count / len(df), 4)

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
