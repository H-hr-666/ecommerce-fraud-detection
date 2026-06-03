"""
分析结果API路由
基于真实数据集计算所有分析结果
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import numpy as np
import logging

from services.data_service import load_dataset, clean_data
from services.feature_service import engineer_features, standardize_features
from services.model_service import get_all_models, predict_anomaly_scores
from services.evaluation_service import (
    get_top_risk_orders, get_time_distribution,
    get_device_distribution
)
from services.summary_service import generate_summary
from utils.helpers import format_response, paginate_list
from config import DEFAULT_THRESHOLD

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

# 全局阈值状态
current_threshold = {"value": DEFAULT_THRESHOLD}


@router.get("/top-risk-orders")
async def get_top_risk_orders_api(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, description="每页数量"),
    threshold: Optional[float] = Query(None, ge=0, le=1, description="异常阈值")
):
    """
    获取高风险刷单订单列表（基于真实数据）

    Args:
        page: 页码
        page_size: 每页数量
        threshold: 异常阈值

    Returns:
        分页订单列表
    """
    try:
        from routers.model_router import training_state

        # 使用指定阈值或默认阈值
        thresh = threshold if threshold is not None else current_threshold["value"]

        # 检查是否已训练
        if training_state["anomaly_scores"] is None:
            return format_response({
                "items": [],
                "total": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0,
                "message": "请先训练模型"
            })

        # 获取真实数据
        df_cleaned = training_state["df_original"]
        scores = training_state["anomaly_scores"]["isolation_forest"]

        # 获取Top100高风险订单
        top_orders = get_top_risk_orders(df_cleaned, scores, n_top=100)

        # 添加阈值标记
        for order in top_orders:
            order["is_high_risk"] = order["anomaly_score"] >= thresh

        # 分页
        paginated = paginate_list(top_orders, page, page_size)

        return format_response(paginated)
    except Exception as e:
        logger.error(f"获取高风险订单失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/time-distribution")
async def get_time_distribution_api(
    threshold: Optional[float] = Query(None, ge=0, le=1)
):
    """
    获取高风险订单时段分布（基于真实数据）

    Returns:
        24小时分布数据
    """
    try:
        from routers.model_router import training_state

        thresh = threshold if threshold is not None else current_threshold["value"]

        # 检查是否已训练
        if training_state["anomaly_scores"] is None:
            return format_response({
                "hours": list(range(24)),
                "counts": [0] * 24,
                "rush_hour_ratio": 0,
                "message": "请先训练模型"
            })

        # 获取真实数据
        df_cleaned = training_state["df_original"]
        scores = training_state["anomaly_scores"]["isolation_forest"]

        # 获取真实时段分布
        distribution = get_time_distribution(df_cleaned, scores, thresh)

        return format_response(distribution)
    except Exception as e:
        logger.error(f"获取时段分布失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/device-distribution")
async def get_device_distribution_api(
    threshold: Optional[float] = Query(None, ge=0, le=1)
):
    """
    获取高风险订单设备分布（基于真实数据）

    Returns:
        设备类型分布数据
    """
    try:
        from routers.model_router import training_state

        thresh = threshold if threshold is not None else current_threshold["value"]

        # 检查是否已训练
        if training_state["anomaly_scores"] is None:
            return format_response({
                "devices": [],
                "counts": [],
                "message": "请先训练模型"
            })

        # 获取真实数据
        df_cleaned = training_state["df_original"]
        scores = training_state["anomaly_scores"]["isolation_forest"]

        # 获取真实设备分布
        distribution = get_device_distribution(df_cleaned, scores, thresh)

        return format_response(distribution)
    except Exception as e:
        logger.error(f"获取设备分布失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/overview")
async def get_analysis_overview(
    threshold: Optional[float] = Query(None, ge=0, le=1)
):
    """
    获取分析概览数据（基于真实数据）

    Returns:
        总订单数、疑似刷单数、异常占比、模型指标
    """
    try:
        from routers.model_router import training_state

        thresh = threshold if threshold is not None else current_threshold["value"]

        # 检查是否已训练
        if training_state["metrics"] is None:
            return format_response({
                "total_orders": 0,
                "cleaned_samples": 0,
                "removed_samples": 0,
                "suspicious_orders": 0,
                "anomaly_ratio": 0,
                "threshold": thresh,
                "model_metrics": {
                    "precision": 0,
                    "recall": 0,
                    "f1": 0
                },
                "message": "请先训练模型"
            })

        # 获取真实数据
        df = load_dataset()
        df_cleaned = training_state["df_original"]
        scores = training_state["anomaly_scores"]["isolation_forest"]
        metrics = training_state["metrics"]

        # 计算真实统计
        total_orders = len(df)
        cleaned_samples = len(df_cleaned)
        removed_samples = total_orders - cleaned_samples
        suspicious_orders = int((scores >= thresh).sum())
        anomaly_ratio = round(suspicious_orders / cleaned_samples, 4)

        overview = {
            "total_orders": total_orders,
            "cleaned_samples": cleaned_samples,
            "removed_samples": removed_samples,
            "suspicious_orders": suspicious_orders,
            "anomaly_ratio": anomaly_ratio,
            "threshold": thresh,
            "model_metrics": {
                "precision": metrics["isolation_forest"]["precision"],
                "recall": metrics["isolation_forest"]["recall"],
                "f1": metrics["isolation_forest"]["f1"]
            }
        }

        return format_response(overview)
    except Exception as e:
        logger.error(f"获取分析概览失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/threshold")
async def update_threshold(threshold: float = Query(..., ge=0, le=1)):
    """
    更新异常分数阈值

    Args:
        threshold: 新的阈值（0-1）

    Returns:
        更新结果
    """
    global current_threshold

    old_threshold = current_threshold["value"]
    current_threshold["value"] = threshold

    logger.info(f"阈值已更新: {old_threshold} -> {threshold}")

    return format_response({
        "old_threshold": old_threshold,
        "new_threshold": threshold
    }, "阈值更新成功")


@router.get("/ai-summary")
async def get_ai_summary(
    threshold: Optional[float] = Query(None, ge=0, le=1, description="异常阈值")
):
    """
    生成 AI 智能综述报告

    基于当前训练结果和分析数据，自动生成结构化的分析报告，
    包含数据概览、模型评估、特征分析、风险发现和建议。

    Returns:
        结构化综述数据
    """
    try:
        from routers.model_router import training_state

        thresh = threshold if threshold is not None else current_threshold["value"]

        # 收集概览数据
        if training_state["metrics"] is not None:
            df = load_dataset()
            df_cleaned = training_state["df_original"]
            scores = training_state["anomaly_scores"]["isolation_forest"]
            metrics = training_state["metrics"]

            total_orders = len(df)
            cleaned_samples = len(df_cleaned)
            removed_samples = total_orders - cleaned_samples
            suspicious_orders = int((scores >= thresh).sum())
            anomaly_ratio = round(suspicious_orders / cleaned_samples, 4)

            overview = {
                "total_orders": total_orders,
                "cleaned_samples": cleaned_samples,
                "removed_samples": removed_samples,
                "suspicious_orders": suspicious_orders,
                "anomaly_ratio": anomaly_ratio
            }
        else:
            overview = {
                "total_orders": 0,
                "cleaned_samples": 0,
                "removed_samples": 0,
                "suspicious_orders": 0,
                "anomaly_ratio": 0
            }
            metrics = None

        # 收集特征重要性
        feature_importance = training_state.get("feature_importance") or {}

        # 收集高风险订单
        top_orders = []
        if training_state["anomaly_scores"] is not None and training_state["df_original"] is not None:
            top_orders = get_top_risk_orders(
                training_state["df_original"],
                training_state["anomaly_scores"]["isolation_forest"],
                n_top=50
            )

        # 收集时段分布
        time_dist = {}
        if training_state["anomaly_scores"] is not None and training_state["df_original"] is not None:
            time_dist = get_time_distribution(
                training_state["df_original"],
                training_state["anomaly_scores"]["isolation_forest"],
                thresh
            )

        # 收集设备分布
        device_dist = {}
        if training_state["anomaly_scores"] is not None and training_state["df_original"] is not None:
            device_dist = get_device_distribution(
                training_state["df_original"],
                training_state["anomaly_scores"]["isolation_forest"],
                thresh
            )

        # 生成综述
        result = generate_summary(
            overview=overview,
            metrics=metrics,
            feature_importance=feature_importance,
            top_orders=top_orders,
            time_dist=time_dist,
            device_dist=device_dist,
            threshold=thresh
        )

        return format_response(result)

    except Exception as e:
        logger.error(f"生成 AI 综述失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
