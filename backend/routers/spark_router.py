"""
Spark 相关 API 路由
提供 Spark SQL 分析、MLlib 训练、Streaming 检测的接口
"""

from fastapi import APIRouter, HTTPException, Query
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

from utils.helpers import format_response
from config import DATASET_PATH

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spark", tags=["spark"])

# 线程池用于执行 Spark 阻塞操作
executor = ThreadPoolExecutor(max_workers=4)

# Spark 结果缓存
_spark_cache = {
    "sql_results": None,
    "mllib_results": None
}


def _get_spark():
    """获取 SparkSession（懒加载）"""
    from spark_modules.spark_session import get_spark_session
    return get_spark_session()


# ==================== 健康检查 ====================

@router.get("/health")
async def spark_health():
    """检查 SparkSession 可用性"""
    try:
        spark = _get_spark()
        return format_response({
            "status": "healthy",
            "spark_version": spark.version,
            "master": spark.sparkContext.master
        })
    except Exception as e:
        logger.error(f"Spark 健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Spark SQL 分析 ====================

@router.get("/sql/descriptive-stats")
async def spark_descriptive_stats():
    """Spark SQL 描述性统计"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, _run_descriptive_stats)
        return format_response(result)
    except Exception as e:
        logger.error(f"描述性统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_descriptive_stats():
    from spark_modules.spark_sql_analysis import load_data_to_spark, descriptive_stats
    spark = _get_spark()
    load_data_to_spark(spark, DATASET_PATH)
    return descriptive_stats(spark)


@router.get("/sql/hourly-distribution")
async def spark_hourly_distribution():
    """Spark SQL 小时分布分析"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, _run_hourly_distribution)
        return format_response(result)
    except Exception as e:
        logger.error(f"小时分布分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_hourly_distribution():
    from spark_modules.spark_sql_analysis import load_data_to_spark, hourly_distribution
    spark = _get_spark()
    load_data_to_spark(spark, DATASET_PATH)
    return hourly_distribution(spark)


@router.get("/sql/device-analysis")
async def spark_device_analysis():
    """Spark SQL 设备类型分析"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, _run_device_analysis)
        return format_response(result)
    except Exception as e:
        logger.error(f"设备分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_device_analysis():
    from spark_modules.spark_sql_analysis import load_data_to_spark, device_analysis
    spark = _get_spark()
    load_data_to_spark(spark, DATASET_PATH)
    return device_analysis(spark)


@router.get("/sql/user-profiling")
async def spark_user_profiling(
    limit: int = Query(default=100, ge=1, le=1000, description="返回用户数量上限")
):
    """Spark SQL 用户行为画像"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, _run_user_profiling, limit)
        return format_response(result)
    except Exception as e:
        logger.error(f"用户画像分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_user_profiling(limit):
    from spark_modules.spark_sql_analysis import load_data_to_spark, user_profiling
    spark = _get_spark()
    load_data_to_spark(spark, DATASET_PATH)
    return user_profiling(spark, limit)


@router.get("/sql/anomaly-segmentation")
async def spark_anomaly_segmentation():
    """Spark SQL 异常分数分段分析"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, _run_anomaly_segmentation)
        return format_response(result)
    except Exception as e:
        logger.error(f"异常分段分析失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _run_anomaly_segmentation():
    from spark_modules.spark_sql_analysis import load_data_to_spark, anomaly_segmentation
    spark = _get_spark()
    load_data_to_spark(spark, DATASET_PATH)
    return anomaly_segmentation(spark)


# ==================== Spark MLlib 训练 ====================

@router.post("/mllib/train")
async def train_spark_models():
    """训练 Spark MLlib 模型（KMeans + GMM）"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(executor, _train_spark_models)
        _spark_cache["mllib_results"] = result
        return format_response(result, "Spark MLlib 模型训练完成")
    except Exception as e:
        logger.error(f"Spark MLlib 训练失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _train_spark_models():
    from spark_modules.spark_mllib_training import train_all_spark_models
    spark = _get_spark()
    return train_all_spark_models(spark, DATASET_PATH)


@router.get("/mllib/compare")
async def get_mllib_comparison():
    """获取 Spark MLlib vs sklearn 模型对比"""
    try:
        if _spark_cache["mllib_results"] is None:
            return format_response({
                "message": "请先训练 Spark 模型",
                "algorithms": [],
                "train_time": [],
                "avg_anomaly_score": []
            })

        from spark_modules.spark_mllib_training import compare_with_sklearn

        # 尝试获取 sklearn 训练结果
        sklearn_metrics = None
        try:
            from routers.model_router import training_state
            if training_state.get("metrics"):
                sklearn_metrics = training_state["metrics"]
        except Exception:
            pass

        comparison = compare_with_sklearn(_spark_cache["mllib_results"], sklearn_metrics)
        return format_response(comparison)

    except Exception as e:
        logger.error(f"获取模型对比失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ==================== Spark Streaming ====================

@router.post("/streaming/start")
async def start_streaming(
    rows_per_second: int = Query(default=5, ge=1, le=100, description="每秒生成行数")
):
    """启动实时流检测"""
    try:
        loop = asyncio.get_running_loop()
        result = await loop.run_in_executor(
            executor, _start_streaming, rows_per_second
        )
        return format_response(result)
    except Exception as e:
        logger.error(f"启动 Streaming 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _start_streaming(rows_per_second):
    from spark_modules.spark_streaming import start_rate_streaming
    spark = _get_spark()
    return start_rate_streaming(spark, rows_per_second)


@router.post("/streaming/stop")
async def stop_streaming_endpoint():
    """停止实时流检测"""
    try:
        from spark_modules.spark_streaming import stop_streaming as _stop
        result = _stop()
        return format_response(result)
    except Exception as e:
        logger.error(f"停止 Streaming 失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streaming/status")
async def get_streaming_status():
    """获取 Streaming 运行状态"""
    try:
        from spark_modules.spark_streaming import get_streaming_status as _status
        return format_response(_status())
    except Exception as e:
        logger.error(f"获取 Streaming 状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streaming/results")
async def get_streaming_results(
    limit: int = Query(default=50, ge=1, le=500, description="返回结果数量上限")
):
    """获取最新实时检测结果"""
    try:
        from spark_modules.spark_streaming import get_streaming_results as _results
        return format_response(_results(limit))
    except Exception as e:
        logger.error(f"获取 Streaming 结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/streaming/statistics")
async def get_streaming_statistics():
    """获取 Streaming 结果统计"""
    try:
        from spark_modules.spark_streaming import get_streaming_statistics as _stats
        return format_response(_stats())
    except Exception as e:
        logger.error(f"获取 Streaming 统计失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
