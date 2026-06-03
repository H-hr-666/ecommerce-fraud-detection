"""
Spark SQL 数据分析模块
使用 Spark SQL 进行多维度订单数据分析
支持数据缓存，避免重复加载
"""

import logging
from typing import Dict, List, Optional

from pyspark.sql import SparkSession, DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)

# 数据缓存：避免每次 API 调用都重新加载 CSV
_cached_df = None
_cached_csv_path = None


def load_data_to_spark(spark: SparkSession, csv_path: str) -> DataFrame:
    """
    加载 CSV 数据到 Spark DataFrame 并注册临时视图
    使用缓存机制，相同路径只加载一次

    Args:
        spark: SparkSession 实例
        csv_path: CSV 文件路径

    Returns:
        Spark DataFrame
    """
    global _cached_df, _cached_csv_path

    if _cached_df is not None and _cached_csv_path == csv_path:
        _cached_df.createOrReplaceTempView("orders")
        return _cached_df

    logger.info(f"加载数据到 Spark: {csv_path}")
    _cached_df = spark.read.csv(csv_path, header=True, inferSchema=True)
    _cached_df.createOrReplaceTempView("orders")
    _cached_csv_path = csv_path
    logger.info("数据加载完成")
    return _cached_df


def invalidate_cache():
    """清除数据缓存（数据集更新时调用）"""
    global _cached_df, _cached_csv_path
    _cached_df = None
    _cached_csv_path = None
    logger.info("Spark 数据缓存已清除")


def descriptive_stats(spark: SparkSession) -> Dict:
    """
    使用 Spark SQL 计算描述性统计

    Returns:
        包含均值、标准差、最值等统计信息的字典
    """
    result = spark.sql("""
        SELECT
            COUNT(*) as sample_count,
            ROUND(AVG(amount), 2) as amount_mean,
            ROUND(STDDEV(amount), 2) as amount_std,
            ROUND(MIN(amount), 2) as amount_min,
            ROUND(MAX(amount), 2) as amount_max,
            ROUND(PERCENTILE_APPROX(amount, 0.5), 2) as amount_median,
            ROUND(AVG(time_diff), 2) as time_diff_mean,
            ROUND(STDDEV(time_diff), 2) as time_diff_std,
            ROUND(MIN(time_diff), 2) as time_diff_min,
            ROUND(MAX(time_diff), 2) as time_diff_max,
            ROUND(PERCENTILE_APPROX(time_diff, 0.5), 2) as time_diff_median,
            ROUND(AVG(CASE WHEN order_time BETWEEN 1 AND 6 THEN 1.0 ELSE 0.0 END), 4) as rush_hour_ratio
        FROM orders
        WHERE amount IS NOT NULL AND time_diff IS NOT NULL
    """)
    row = result.collect()[0]
    return {
        "sample_count": row["sample_count"],
        "amount": {
            "mean": row["amount_mean"],
            "std": row["amount_std"],
            "min": row["amount_min"],
            "max": row["amount_max"],
            "median": row["amount_median"]
        },
        "time_diff": {
            "mean": row["time_diff_mean"],
            "std": row["time_diff_std"],
            "min": row["time_diff_min"],
            "max": row["time_diff_max"],
            "median": row["time_diff_median"]
        },
        "rush_hour_ratio": row["rush_hour_ratio"]
    }


def hourly_distribution(spark: SparkSession) -> Dict:
    """
    使用 Spark SQL 计算每小时订单分布

    Returns:
        包含小时和订单数量的字典
    """
    result = spark.sql("""
        SELECT
            order_time as hour,
            COUNT(*) as order_count,
            ROUND(AVG(amount), 2) as avg_amount,
            ROUND(AVG(time_diff), 2) as avg_time_diff
        FROM orders
        WHERE amount IS NOT NULL AND time_diff IS NOT NULL
        GROUP BY order_time
        ORDER BY order_time
    """)
    rows = result.collect()
    return {
        "hours": [row["hour"] for row in rows],
        "order_counts": [row["order_count"] for row in rows],
        "avg_amounts": [row["avg_amount"] for row in rows],
        "avg_time_diffs": [row["avg_time_diff"] for row in rows]
    }


def device_analysis(spark: SparkSession) -> Dict:
    """
    使用 Spark SQL 进行设备类型分析

    Returns:
        各设备类型的统计信息
    """
    result = spark.sql("""
        SELECT
            device_type,
            COUNT(*) as order_count,
            ROUND(AVG(amount), 2) as avg_amount,
            ROUND(STDDEV(amount), 2) as std_amount,
            ROUND(AVG(time_diff), 2) as avg_time_diff,
            ROUND(AVG(CASE WHEN order_time BETWEEN 1 AND 6 THEN 1.0 ELSE 0.0 END), 4) as rush_hour_ratio
        FROM orders
        WHERE amount IS NOT NULL AND time_diff IS NOT NULL
        GROUP BY device_type
        ORDER BY order_count DESC
    """)
    rows = result.collect()
    return {
        "devices": [row["device_type"] for row in rows],
        "order_counts": [row["order_count"] for row in rows],
        "avg_amounts": [row["avg_amount"] for row in rows],
        "std_amounts": [row["std_amount"] for row in rows],
        "avg_time_diffs": [row["avg_time_diff"] for row in rows],
        "rush_hour_ratios": [row["rush_hour_ratio"] for row in rows]
    }


def user_profiling(spark: SparkSession, limit: int = 100) -> List[Dict]:
    """
    使用 Spark SQL 进行用户行为画像分析

    识别可疑用户：订单量大、时间间隔短、凌晨下单多

    Args:
        limit: 返回用户数量上限（1-1000）

    Returns:
        用户画像列表
    """
    # 参数校验，防止 SQL 注入
    limit = max(1, min(1000, int(limit)))

    result = spark.sql(f"""
        SELECT
            user_id,
            COUNT(*) as order_count,
            ROUND(AVG(amount), 2) as avg_amount,
            ROUND(SUM(amount), 2) as total_amount,
            ROUND(AVG(time_diff), 2) as avg_time_diff,
            ROUND(MIN(time_diff), 2) as min_time_diff,
            SUM(CASE WHEN order_time BETWEEN 1 AND 6 THEN 1 ELSE 0 END) as rush_hour_orders,
            COUNT(DISTINCT device_type) as device_count,
            COUNT(DISTINCT order_id) as unique_orders
        FROM orders
        WHERE amount IS NOT NULL AND time_diff IS NOT NULL
        GROUP BY user_id
        HAVING COUNT(*) > 1
        ORDER BY order_count DESC, avg_time_diff ASC
        LIMIT {limit}
    """)
    rows = result.collect()
    return [
        {
            "user_id": row["user_id"],
            "order_count": row["order_count"],
            "avg_amount": row["avg_amount"],
            "total_amount": row["total_amount"],
            "avg_time_diff": row["avg_time_diff"],
            "min_time_diff": row["min_time_diff"],
            "rush_hour_orders": row["rush_hour_orders"],
            "device_count": row["device_count"],
            "unique_orders": row["unique_orders"]
        }
        for row in rows
    ]


def anomaly_segmentation(spark: SparkSession, scores: Optional[List[float]] = None) -> Dict:
    """
    使用 Spark SQL 进行异常分数分段分析

    将订单按异常分数分为 5 个区间，分析各区间的特征分布

    Args:
        scores: 异常分数列表（可选，如果提供则与原始数据关联）

    Returns:
        分段统计结果
    """
    if scores is not None:
        # 将分数列表转为 DataFrame 并通过行号关联
        import pandas as pd
        pdf = pd.DataFrame({"anomaly_score": scores})
        scores_df = spark.createDataFrame(pdf)
        # 从 temp view 获取 orders DataFrame，使用 row_number 窗口函数生成可靠行号
        orders_df = spark.table("orders")
        orders_with_id = orders_df.withColumn("_row_id", F.row_number().over(Window.orderBy(F.monotonically_increasing_id())))
        scores_with_id = scores_df.withColumn("_row_id", F.row_number().over(Window.orderBy(F.monotonically_increasing_id())))

        joined_df = orders_with_id.join(scores_with_id, on="_row_id", how="inner")
        joined_df.createOrReplaceTempView("orders_with_scores")

        result = spark.sql("""
            SELECT
                CASE
                    WHEN anomaly_score < 0.2 THEN '0-0.2'
                    WHEN anomaly_score < 0.4 THEN '0.2-0.4'
                    WHEN anomaly_score < 0.6 THEN '0.4-0.6'
                    WHEN anomaly_score < 0.8 THEN '0.6-0.8'
                    ELSE '0.8-1.0'
                END as score_bucket,
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg_amount,
                ROUND(AVG(time_diff), 2) as avg_time_diff,
                ROUND(AVG(CASE WHEN order_time BETWEEN 1 AND 6 THEN 1.0 ELSE 0.0 END), 4) as rush_hour_ratio
            FROM orders_with_scores
            WHERE amount IS NOT NULL AND time_diff IS NOT NULL
            GROUP BY score_bucket
            ORDER BY score_bucket
        """)
    else:
        # 无分数时，基于 amount 分位数模拟分段
        result = spark.sql("""
            SELECT
                CASE
                    WHEN amount < 50 THEN '低金额(<50)'
                    WHEN amount < 200 THEN '中低金额(50-200)'
                    WHEN amount < 500 THEN '中金额(200-500)'
                    WHEN amount < 1000 THEN '中高金额(500-1000)'
                    ELSE '高金额(>1000)'
                END as score_bucket,
                COUNT(*) as count,
                ROUND(AVG(amount), 2) as avg_amount,
                ROUND(AVG(time_diff), 2) as avg_time_diff,
                ROUND(AVG(CASE WHEN order_time BETWEEN 1 AND 6 THEN 1.0 ELSE 0.0 END), 4) as rush_hour_ratio
            FROM orders
            WHERE amount IS NOT NULL AND time_diff IS NOT NULL
            GROUP BY score_bucket
            ORDER BY score_bucket
        """)

    rows = result.collect()
    return {
        "buckets": [row["score_bucket"] for row in rows],
        "counts": [row["count"] for row in rows],
        "avg_amounts": [row["avg_amount"] for row in rows],
        "avg_time_diffs": [row["avg_time_diff"] for row in rows],
        "rush_hour_ratios": [row["rush_hour_ratio"] for row in rows]
    }
