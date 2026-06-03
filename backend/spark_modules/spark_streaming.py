"""
Spark Structured Streaming 实时检测模块
使用 Rate 源生成模拟订单流，实时计算异常分数
支持加载预训练 KMeans 模型进行 ML 检测，回退到规则检测
"""

import os
import logging
import time
import threading
from collections import deque
from typing import Dict, List, Optional

import numpy as np
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType

from config import SPARK_CONFIG, SPARK_STREAMING_CHECKPOINT_DIR

logger = logging.getLogger(__name__)

# 线程安全的结果缓冲区
_streaming_results = deque(maxlen=SPARK_CONFIG["streaming_buffer_size"])
_streaming_query = None
_streaming_lock = threading.Lock()
_streaming_status = {
    "is_running": False,
    "start_time": None,
    "processed_batches": 0,
    "total_records": 0,
    "detection_mode": "rule"  # "rule" 或 "ml"
}

# 预训练模型缓存
_kmeans_model = None


def _load_kmeans_model():
    """尝试加载预训练的 KMeans 模型"""
    global _kmeans_model
    if _kmeans_model is not None:
        return _kmeans_model

    try:
        from spark_modules.spark_mllib_training import load_kmeans_model_for_streaming
        _kmeans_model = load_kmeans_model_for_streaming()
        if _kmeans_model is not None:
            logger.info("Streaming 已加载 KMeans 预训练模型")
        return _kmeans_model
    except Exception as e:
        logger.warning(f"加载 KMeans 模型失败，使用规则检测: {e}")
        return None


def start_rate_streaming(spark: SparkSession, rows_per_second: int = 5) -> Dict:
    """
    启动 Rate 源实时流，模拟订单数据并计算异常分数

    优先使用预训练 KMeans 模型，如果不可用则回退到规则检测

    Args:
        spark: SparkSession 实例
        rows_per_second: 每秒生成的行数

    Returns:
        启动状态信息
    """
    global _streaming_query, _streaming_status

    if _streaming_status["is_running"]:
        return {"status": "already_running", "message": "Streaming 已在运行中"}

    try:
        # 尝试加载 KMeans 模型
        kmeans_model = _load_kmeans_model()
        use_ml = kmeans_model is not None

        stream_df = (
            spark.readStream
            .format("rate")
            .option("rowsPerSecond", rows_per_second)
            .option("numPartitions", 2)
            .load()
        )

        # 生成模拟订单字段（修正设备概率分布）
        stream_df = (
            stream_df
            .withColumn("user_id",
                        F.concat(F.lit("U"), F.lpad(F.col("value") % 1000, 6, "0")))
            .withColumn("order_id",
                        F.concat(F.lit("O"), F.lpad(F.col("value"), 8, "0")))
            .withColumn("amount",
                        F.when(F.rand() < 0.05, F.rand() * 10 + 1)  # 5% 异常低金额
                        .otherwise(F.rand() * 1000 + 10))
            .withColumn("time_diff",
                        F.when(F.rand() < 0.05, F.rand() * 2)  # 5% 异常短间隔
                        .otherwise(F.rand() * 300 + 10))
            .withColumn("order_time",
                        F.when(F.rand() < 0.1, (F.rand() * 5 + 1).cast("int"))  # 10% 凌晨
                        .otherwise((F.rand() * 18 + 6).cast("int")))
            .withColumn("device_type",
                        F.when(F.rand() < 0.40, "Android")
                        .when(F.rand() < 0.70, "iOS")
                        .when(F.rand() < 0.90, "PC")
                        .otherwise("H5"))
        )

        # 特征工程
        stream_df = (
            stream_df
            .withColumn("log_amount", F.log1p(F.col("amount")))
            .withColumn("is_rush_hour",
                        F.when(F.col("order_time").between(1, 6), 1).otherwise(0))
            .withColumn("device_encoded",
                        F.when(F.col("device_type") == "iOS", 0)
                        .when(F.col("device_type") == "Android", 1)
                        .when(F.col("device_type") == "PC", 2)
                        .otherwise(3))
        )

        if use_ml:
            # ML 模式：使用 KMeans 模型计算异常分数
            from pyspark.ml.feature import VectorAssembler
            assembler = VectorAssembler(
                inputCols=["log_amount", "time_diff", "is_rush_hour", "device_encoded"],
                outputCol="features"
            )
            stream_df = assembler.transform(stream_df)

            # 使用预训练模型预测
            predictions = kmeans_model.transform(stream_df)

            # 计算到聚类中心的距离
            centers = kmeans_model.clusterCenters()
            from pyspark.ml.functions import vector_to_array
            predictions = predictions.withColumn("features_array", vector_to_array("features"))

            # 向量化距离计算
            for i, center in enumerate(centers):
                center_list = [float(c) for c in center]
                squared_diffs = sum(
                    (F.col("features_array")[j] - F.lit(center_list[j])) ** 2
                    for j in range(len(center_list))
                )
                predictions = predictions.withColumn(f"dist_{i}", F.sqrt(squared_diffs))

            dist_cols = [F.col(f"dist_{i}") for i in range(len(centers))]
            predictions = predictions.withColumn(
                "anomaly_score",
                F.least(*dist_cols)
            )

            # 简单归一化（使用固定范围，避免流式计算中的全局统计）
            predictions = predictions.withColumn(
                "anomaly_score",
                F.least(F.lit(1.0), F.col("anomaly_score") / F.lit(5.0))
            )
            predictions = predictions.withColumn(
                "is_anomaly", F.when(F.col("anomaly_score") > 0.5, 1).otherwise(0)
            )

            # 清理临时列
            dist_drop = [f"dist_{i}" for i in range(len(centers))] + ["features_array", "features", "raw_features"]
            predictions = predictions.drop(*[c for c in dist_drop if c in predictions.columns])

            stream_df = predictions
            _streaming_status["detection_mode"] = "ml"
            logger.info("Streaming 使用 ML 模式 (KMeans)")
        else:
            # 规则模式
            stream_df = (
                stream_df
                .withColumn("score_amount",
                            F.when(F.col("amount") < 20, 0.4).otherwise(0.1))
                .withColumn("score_time",
                            F.when(F.col("time_diff") < 5, 0.4).otherwise(0.1))
                .withColumn("score_rush",
                            F.when(F.col("is_rush_hour") == 1, 0.2).otherwise(0.0))
                .withColumn("anomaly_score",
                            F.least(F.lit(1.0),
                                    F.col("score_amount") + F.col("score_time") + F.col("score_rush")))
                .withColumn("is_anomaly", F.when(F.col("anomaly_score") > 0.5, 1).otherwise(0))
            )
            _streaming_status["detection_mode"] = "rule"
            logger.info("Streaming 使用规则模式")

        # 确保 checkpoint 目录存在
        os.makedirs(SPARK_STREAMING_CHECKPOINT_DIR, exist_ok=True)

        # 使用 foreachBatch 写入内存缓冲区
        query = (
            stream_df
            .select("user_id", "order_id", "amount", "time_diff",
                    "order_time", "device_type", "anomaly_score", "is_anomaly")
            .writeStream
            .outputMode("append")
            .foreachBatch(_process_batch)
            .trigger(processingTime="2 seconds")
            .option("checkpointLocation", SPARK_STREAMING_CHECKPOINT_DIR)
            .start()
        )

        _streaming_query = query
        _streaming_status["is_running"] = True
        _streaming_status["start_time"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _streaming_status["processed_batches"] = 0
        _streaming_status["total_records"] = 0

        logger.info(f"Streaming 已启动: rowsPerSecond={rows_per_second}, mode={_streaming_status['detection_mode']}")

        return {
            "status": "started",
            "message": f"实时检测已启动，每秒 {rows_per_second} 条订单",
            "start_time": _streaming_status["start_time"],
            "detection_mode": _streaming_status["detection_mode"]
        }

    except Exception as e:
        logger.error(f"Streaming 启动失败: {e}")
        _streaming_status["is_running"] = False
        return {"status": "error", "message": str(e)}


def _process_batch(batch_df: DataFrame, epoch_id: int):
    """
    处理每个微批次的数据，写入内存缓冲区

    Args:
        batch_df: 微批次 DataFrame
        epoch_id: 批次 ID
    """
    global _streaming_status

    try:
        rows = batch_df.collect()
        with _streaming_lock:
            for row in rows:
                _streaming_results.append({
                    "user_id": row["user_id"],
                    "order_id": row["order_id"],
                    "amount": round(row["amount"], 2),
                    "time_diff": round(row["time_diff"], 2),
                    "order_time": row["order_time"],
                    "device_type": row["device_type"],
                    "anomaly_score": round(row["anomaly_score"], 4),
                    "is_anomaly": bool(row["is_anomaly"]),
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                })
            _streaming_status["processed_batches"] += 1
            _streaming_status["total_records"] += len(rows)

        logger.debug(f"批次 {epoch_id}: 处理 {len(rows)} 条记录")

    except Exception as e:
        logger.error(f"批次处理失败: {e}")


def stop_streaming() -> Dict:
    """
    停止 Streaming 查询

    Returns:
        停止状态信息
    """
    global _streaming_query, _streaming_status

    if _streaming_query is None or not _streaming_status["is_running"]:
        return {"status": "not_running", "message": "Streaming 未在运行"}

    try:
        _streaming_query.stop()
        _streaming_query = None
        _streaming_status["is_running"] = False

        logger.info("Streaming 已停止")
        return {
            "status": "stopped",
            "message": "实时检测已停止",
            "total_processed": _streaming_status["total_records"]
        }

    except Exception as e:
        logger.error(f"Streaming 停止失败: {e}")
        return {"status": "error", "message": str(e)}


def get_streaming_status() -> Dict:
    """
    获取 Streaming 运行状态

    Returns:
        状态信息字典
    """
    return {
        "is_running": _streaming_status["is_running"],
        "start_time": _streaming_status["start_time"],
        "processed_batches": _streaming_status["processed_batches"],
        "total_records": _streaming_status["total_records"],
        "buffer_size": len(_streaming_results),
        "detection_mode": _streaming_status["detection_mode"]
    }


def get_streaming_results(limit: int = 50) -> List[Dict]:
    """
    获取最新的 Streaming 检测结果

    Args:
        limit: 返回结果数量上限

    Returns:
        最新检测结果列表
    """
    with _streaming_lock:
        results = list(_streaming_results)

    # 返回最新的 limit 条
    return results[-limit:] if len(results) > limit else results


def get_streaming_statistics() -> Dict:
    """
    获取 Streaming 结果的统计信息

    Returns:
        统计信息字典
    """
    with _streaming_lock:
        results = list(_streaming_results)

    if not results:
        return {
            "total_count": 0,
            "anomaly_count": 0,
            "anomaly_ratio": 0,
            "avg_anomaly_score": 0,
            "max_anomaly_score": 0
        }

    scores = [r["anomaly_score"] for r in results]
    anomaly_count = sum(1 for r in results if r["is_anomaly"])

    return {
        "total_count": len(results),
        "anomaly_count": anomaly_count,
        "anomaly_ratio": round(anomaly_count / len(results), 4),
        "avg_anomaly_score": round(np.mean(scores), 4),
        "max_anomaly_score": round(max(scores), 4),
        "min_anomaly_score": round(min(scores), 4)
    }
