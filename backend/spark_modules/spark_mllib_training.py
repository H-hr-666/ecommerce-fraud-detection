"""
Spark MLlib 模型训练模块
使用 KMeans、GMM 进行分布式异常检测
支持模型持久化与 sklearn 对比
"""

import os
import logging
import time
from typing import Dict, List, Tuple, Optional

import numpy as np
from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.ml.feature import VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans, GaussianMixture, KMeansModel
from pyspark.ml.functions import vector_to_array
from pyspark.sql.types import DoubleType

from config import MODEL_DIR

logger = logging.getLogger(__name__)

# Spark 模型存储路径
SPARK_MODEL_DIR = os.path.join(MODEL_DIR, "spark")


def build_feature_pipeline(spark: SparkSession, csv_path: str) -> Tuple[DataFrame, StandardScaler]:
    """
    构建 Spark ML 特征工程 Pipeline

    Args:
        spark: SparkSession 实例
        csv_path: CSV 文件路径

    Returns:
        (特征工程后的 DataFrame, scaler 模型)
    """
    df = spark.read.csv(csv_path, header=True, inferSchema=True)

    # 特征工程（与 feature_service.py 一致）
    df = df.withColumn("log_amount", F.log1p(F.col("amount")))
    df = df.withColumn("is_rush_hour",
                       F.when(F.col("order_time").between(1, 6), 1).otherwise(0))
    df = df.withColumn("device_encoded",
                       F.when(F.col("device_type") == "iOS", 0)
                       .when(F.col("device_type") == "Android", 1)
                       .when(F.col("device_type") == "PC", 2)
                       .otherwise(3))

    df = df.na.drop(subset=["log_amount", "time_diff"])

    assembler = VectorAssembler(
        inputCols=["log_amount", "time_diff", "is_rush_hour", "device_encoded"],
        outputCol="raw_features"
    )
    df = assembler.transform(df)

    scaler = StandardScaler(
        inputCol="raw_features",
        outputCol="features",
        withStd=True,
        withMean=True
    )
    scaler_model = scaler.fit(df)
    df = scaler_model.transform(df)

    logger.info("特征工程完成")
    return df, scaler_model


def train_kmeans(df: DataFrame, k: int = 2) -> Tuple[Dict, any, DataFrame]:
    """
    训练 KMeans 模型用于异常检测

    原理：计算样本到最近聚类中心的距离，距离越大越可能是异常
    使用 PySpark 内置函数向量化计算距离，避免 Python UDF 开销

    Args:
        df: 特征工程后的 DataFrame
        k: 聚类数量

    Returns:
        (训练结果字典, KMeans 模型, 预测结果 DataFrame)
    """
    logger.info(f"开始训练 KMeans (k={k})...")
    start_time = time.time()

    kmeans = KMeans(
        featuresCol="features",
        predictionCol="prediction",
        k=k,
        seed=42,
        maxIter=20
    )
    model = kmeans.fit(df)
    predictions = model.transform(df)

    # 获取聚类中心
    centers = model.clusterCenters()

    # 将 features 向量转为数组，用于向量化距离计算
    predictions = predictions.withColumn("features_array", vector_to_array("features"))

    # 为每个聚类中心创建距离列，取最小距离作为异常分数
    # 使用 PySpark 内置函数替代 Python UDF，性能提升显著
    for i, center in enumerate(centers):
        center_list = [float(c) for c in center]
        # 计算欧氏距离：sqrt(sum((x_i - c_i)^2))
        squared_diffs = sum(
            (F.col("features_array")[j] - F.lit(center_list[j])) ** 2
            for j in range(len(center_list))
        )
        predictions = predictions.withColumn(f"dist_{i}", F.sqrt(squared_diffs))

    # 取到最近聚类中心的距离作为异常分数
    dist_cols = [F.col(f"dist_{i}") for i in range(len(centers))]
    predictions = predictions.withColumn(
        "anomaly_score_raw",
        F.least(*dist_cols)
    )

    # 归一化到 0-1
    stats = predictions.agg(
        F.min("anomaly_score_raw").alias("min_score"),
        F.max("anomaly_score_raw").alias("max_score")
    ).collect()[0]

    min_s, max_s = stats["min_score"], stats["max_score"]
    if max_s > min_s:
        predictions = predictions.withColumn(
            "anomaly_score",
            (F.col("anomaly_score_raw") - min_s) / (max_s - min_s)
        )
    else:
        predictions = predictions.withColumn("anomaly_score", F.lit(0.0))

    # 清理临时列
    dist_cols_to_drop = [f"dist_{i}" for i in range(len(centers))] + ["anomaly_score_raw"]
    predictions = predictions.drop(*dist_cols_to_drop)

    train_time = round(time.time() - start_time, 2)

    # 使用聚合计算统计信息，避免 collect 到驱动端
    stats_row = predictions.agg(
        F.avg("anomaly_score").alias("avg_score"),
        F.stddev("anomaly_score").alias("std_score"),
        F.count("*").alias("total_count"),
        F.sum(F.when(F.col("anomaly_score") > 0.8, 1).otherwise(0)).alias("high_count")
    ).collect()[0]

    avg_score = stats_row["avg_score"]
    std_score = stats_row["std_score"] or 0.0
    high_score_ratio = stats_row["high_count"] / stats_row["total_count"] if stats_row["total_count"] > 0 else 0

    result = {
        "algorithm": "KMeans",
        "k": k,
        "train_time": train_time,
        "avg_anomaly_score": round(avg_score, 4),
        "std_anomaly_score": round(std_score, 4),
        "high_score_ratio": round(high_score_ratio, 4),
        "sample_count": stats_row["total_count"]
    }

    logger.info(f"KMeans 训练完成: 耗时={train_time}s, 平均分={avg_score:.4f}")
    return result, model, predictions


def train_gmm(df: DataFrame, k: int = 2) -> Tuple[Dict, any, DataFrame]:
    """
    训练高斯混合模型 (GMM) 用于异常检测

    原理：低概率密度的样本更可能是异常

    Args:
        df: 特征工程后的 DataFrame
        k: 高斯分量数量

    Returns:
        (训练结果字典, GMM 模型, 预测结果 DataFrame)
    """
    logger.info(f"开始训练 GMM (k={k})...")
    start_time = time.time()

    gmm = GaussianMixture(
        featuresCol="features",
        predictionCol="prediction",
        probabilityCol="probability",
        k=k,
        seed=42,
        maxIter=20
    )
    model = gmm.fit(df)
    predictions = model.transform(df)

    # 提取最大概率，概率越低越可能是异常
    predictions = predictions.withColumn("prob_array", vector_to_array("probability"))
    predictions = predictions.withColumn("max_probability", F.array_max("prob_array"))
    predictions = predictions.withColumn("anomaly_score", 1.0 - F.col("max_probability"))

    train_time = round(time.time() - start_time, 2)

    # 使用聚合计算统计信息
    stats_row = predictions.agg(
        F.avg("anomaly_score").alias("avg_score"),
        F.stddev("anomaly_score").alias("std_score"),
        F.count("*").alias("total_count"),
        F.sum(F.when(F.col("anomaly_score") > 0.8, 1).otherwise(0)).alias("high_count")
    ).collect()[0]

    avg_score = stats_row["avg_score"]
    std_score = stats_row["std_score"] or 0.0
    high_score_ratio = stats_row["high_count"] / stats_row["total_count"] if stats_row["total_count"] > 0 else 0

    result = {
        "algorithm": "GMM",
        "k": k,
        "train_time": train_time,
        "avg_anomaly_score": round(avg_score, 4),
        "std_anomaly_score": round(std_score, 4),
        "high_score_ratio": round(high_score_ratio, 4),
        "sample_count": stats_row["total_count"]
    }

    logger.info(f"GMM 训练完成: 耗时={train_time}s, 平均分={avg_score:.4f}")
    return result, model, predictions


def save_spark_model(model, model_name: str):
    """
    保存 Spark MLlib 模型到磁盘（覆盖已有模型）

    Args:
        model: Spark ML 模型
        model_name: 模型名称（如 'kmeans', 'gmm'）
    """
    os.makedirs(SPARK_MODEL_DIR, exist_ok=True)
    model_path = os.path.join(SPARK_MODEL_DIR, model_name)
    model.write().overwrite().save(model_path)
    logger.info(f"Spark 模型已保存: {model_path}")


def load_spark_model(model_class, model_name: str):
    """
    从磁盘加载 Spark MLlib 模型

    Args:
        model_class: 模型类（如 KMeansModel）
        model_name: 模型名称

    Returns:
        加载的模型，如果不存在返回 None
    """
    model_path = os.path.join(SPARK_MODEL_DIR, model_name)
    if os.path.exists(model_path):
        try:
            model = model_class.load(model_path)
            logger.info(f"Spark 模型已加载: {model_path}")
            return model
        except Exception as e:
            logger.warning(f"加载 Spark 模型失败: {e}")
    return None


def train_all_spark_models(spark: SparkSession, csv_path: str) -> Dict:
    """
    训练所有 Spark MLlib 模型并返回对比结果

    Args:
        spark: SparkSession 实例
        csv_path: CSV 文件路径

    Returns:
        包含所有模型训练结果的字典
    """
    logger.info("=" * 50)
    logger.info("开始 Spark MLlib 模型训练")

    df, scaler_model = build_feature_pipeline(spark, csv_path)

    kmeans_result, kmeans_model, kmeans_predictions = train_kmeans(df, k=2)
    gmm_result, gmm_model, gmm_predictions = train_gmm(df, k=2)

    # 保存模型
    save_spark_model(kmeans_model, "kmeans")
    save_spark_model(gmm_model, "gmm")

    # 采样收集分数（最多 1000 条），避免大数据集 OOM
    sample_count = 1000
    kmeans_scores = [
        row["anomaly_score"]
        for row in kmeans_predictions.select("anomaly_score")
            .limit(sample_count).collect()
    ]
    gmm_scores = [
        row["anomaly_score"]
        for row in gmm_predictions.select("anomaly_score")
            .limit(sample_count).collect()
    ]

    results = {
        "kmeans": kmeans_result,
        "gmm": gmm_result,
        "kmeans_scores": kmeans_scores,
        "gmm_scores": gmm_scores
    }

    logger.info("Spark MLlib 模型训练完成")
    logger.info("=" * 50)

    return results


def compare_with_sklearn(spark_results: Dict, sklearn_metrics: Optional[Dict] = None) -> Dict:
    """
    对比 Spark MLlib 与 sklearn 模型的性能

    统一使用训练耗时和异常分数统计作为对比维度

    Args:
        spark_results: Spark 训练结果
        sklearn_metrics: sklearn 模型指标（可选）

    Returns:
        对比结果字典
    """
    comparison = {
        "algorithms": ["KMeans (Spark)", "GMM (Spark)"],
        "train_time": [
            spark_results["kmeans"]["train_time"],
            spark_results["gmm"]["train_time"]
        ],
        "avg_anomaly_score": [
            spark_results["kmeans"]["avg_anomaly_score"],
            spark_results["gmm"]["avg_anomaly_score"]
        ],
        "std_anomaly_score": [
            spark_results["kmeans"]["std_anomaly_score"],
            spark_results["gmm"]["std_anomaly_score"]
        ],
        "high_score_ratio": [
            spark_results["kmeans"]["high_score_ratio"],
            spark_results["gmm"]["high_score_ratio"]
        ]
    }

    if sklearn_metrics:
        # 添加 sklearn 模型的训练耗时和异常分数统计
        comparison["algorithms"].extend(["Isolation Forest", "LOF", "One-Class SVM"])
        for model_key in ["isolation_forest", "lof", "ocsvm"]:
            if model_key in sklearn_metrics:
                m = sklearn_metrics[model_key]
                comparison["train_time"].append(m.get("train_time", 0))
                comparison["avg_anomaly_score"].append(m.get("avg_anomaly_score", 0))
                comparison["std_anomaly_score"].append(m.get("std_anomaly_score", 0))
                comparison["high_score_ratio"].append(m.get("high_score_ratio", 0))

    return comparison


def load_kmeans_model_for_streaming():
    """
    为 Streaming 模块加载预训练的 KMeans 模型

    Returns:
        KMeansModel 或 None
    """
    return load_spark_model(KMeansModel, "kmeans")
