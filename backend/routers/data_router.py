"""
数据相关API路由
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional
import pandas as pd
import io
import logging

from services.data_service import load_dataset, clean_data, get_descriptive_stats, get_raw_data_info
from services.feature_service import engineer_features, standardize_features
from utils.helpers import format_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/data", tags=["data"])


@router.get("/stats")
async def get_dataset_stats():
    """
    获取数据集统计信息（对标论文表3-1描述性统计）

    Returns:
        样本量、各特征均值/标准差/最大最小值
    """
    try:
        # 加载数据
        df = load_dataset()
        df_cleaned = clean_data(df)

        # 获取描述性统计
        stats = get_descriptive_stats(df_cleaned)

        # 添加原始数据信息
        raw_info = get_raw_data_info(df)
        stats["raw_data"] = raw_info
        stats["cleaned_count"] = len(df_cleaned)
        stats["removed_count"] = len(df) - len(df_cleaned)

        return format_response(stats)
    except Exception as e:
        logger.error(f"获取数据统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/distribution")
async def get_anomaly_distribution():
    """
    获取异常分数分布数据（基于真实训练结果）

    Returns:
        直方图数据（bins, counts）
    """
    try:
        from routers.model_router import training_state
        from services.evaluation_service import get_anomaly_distribution

        # 检查是否已训练
        if training_state["anomaly_scores"] is None:
            return format_response(None, "模型未训练，请先训练模型", 400)

        # 获取孤立森林的异常分数
        scores = training_state["anomaly_scores"]["isolation_forest"]

        # 获取分布数据
        distribution = get_anomaly_distribution(scores)

        return format_response(distribution)
    except Exception as e:
        logger.error(f"获取异常分数分布失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    """
    上传自定义数据集

    Args:
        file: CSV文件

    Returns:
        上传结果
    """
    try:
        # 读取上传的文件
        contents = await file.read()
        df = pd.read_csv(io.StringIO(contents.decode('utf-8')))

        # 验证必要字段
        required_fields = ["amount", "time_diff"]
        missing_fields = [f for f in required_fields if f not in df.columns]

        if missing_fields:
            return format_response(None, f"缺少必要字段: {missing_fields}", 400)

        # 保存文件
        from config import DATASET_PATH
        import os
        os.makedirs(os.path.dirname(DATASET_PATH), exist_ok=True)
        df.to_csv(DATASET_PATH, index=False)

        return format_response({
            "filename": file.filename,
            "rows": len(df),
            "columns": list(df.columns)
        }, "数据集上传成功")

    except Exception as e:
        logger.error(f"上传数据集失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
