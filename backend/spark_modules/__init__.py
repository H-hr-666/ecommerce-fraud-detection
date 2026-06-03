"""
Spark 功能模块包

模块说明:
- spark_session: SparkSession 单例管理
- spark_sql_analysis: Spark SQL 多维度数据分析
- spark_mllib_training: Spark MLlib 模型训练（KMeans、GMM）
- spark_streaming: Spark Structured Streaming 实时检测
"""

from spark_modules.spark_session import get_spark_session, stop_spark_session
from spark_modules.spark_sql_analysis import (
    load_data_to_spark,
    invalidate_cache,
    descriptive_stats,
    hourly_distribution,
    device_analysis,
    user_profiling,
    anomaly_segmentation,
)
from spark_modules.spark_mllib_training import (
    train_all_spark_models,
    compare_with_sklearn,
    save_spark_model,
    load_spark_model,
)
from spark_modules.spark_streaming import (
    start_rate_streaming,
    stop_streaming,
    get_streaming_status,
    get_streaming_results,
    get_streaming_statistics,
)

__all__ = [
    "get_spark_session",
    "stop_spark_session",
    "load_data_to_spark",
    "invalidate_cache",
    "descriptive_stats",
    "hourly_distribution",
    "device_analysis",
    "user_profiling",
    "anomaly_segmentation",
    "train_all_spark_models",
    "compare_with_sklearn",
    "save_spark_model",
    "load_spark_model",
    "start_rate_streaming",
    "stop_streaming",
    "get_streaming_status",
    "get_streaming_results",
    "get_streaming_statistics",
]
