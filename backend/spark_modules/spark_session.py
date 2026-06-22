"""
SparkSession 单例管理模块
懒加载初始化，Local 模式运行，内存受限配置
线程安全的单例模式，支持健康检查
"""

import threading
import logging
from pyspark.sql import SparkSession

from config import SPARK_CONFIG, SPARK_REMOTE_MASTER, SPARK_USE_REMOTE

logger = logging.getLogger(__name__)

# 模块级单例引用与线程锁
_spark_session = None
_spark_lock = threading.Lock()


def get_spark_session(app_name: str = "EcommerceFraudDetection") -> SparkSession:
    """
    获取或创建 SparkSession 单例（线程安全）

    使用 Local[*] 模式，从 SPARK_CONFIG 读取配置

    Args:
        app_name: Spark 应用名称

    Returns:
        SparkSession 实例
    """
    global _spark_session

    if _spark_session is not None:
        # 健康检查：尝试获取版本号验证 session 有效性
        try:
            _ = _spark_session.version
            return _spark_session
        except Exception:
            logger.warning("SparkSession 已失效，重新创建...")
            _spark_session = None

    with _spark_lock:
        # 双重检查锁定
        if _spark_session is not None:
            return _spark_session

        # 根据配置选择 master
        if SPARK_USE_REMOTE:
            master_url = SPARK_REMOTE_MASTER
            logger.info(f"正在创建 SparkSession (远程模式: {master_url})...")
        else:
            master_url = "local[*]"
            logger.info("正在创建 SparkSession (Local 模式)...")

        builder = (
            SparkSession.builder
            .appName(app_name)
            .master(master_url)
            .config("spark.driver.memory", SPARK_CONFIG["driver_memory"])
            .config("spark.executor.memory", SPARK_CONFIG["driver_memory"])
            .config("spark.sql.shuffle.partitions", str(SPARK_CONFIG["shuffle_partitions"]))
            .config("spark.default.parallelism", str(SPARK_CONFIG["shuffle_partitions"]))
            .config("spark.ui.enabled", "false")
            .config("spark.eventLog.enabled", "false")
            .config("spark.sql.execution.arrow.pyspark.enabled", "true")
        )

        if SPARK_USE_REMOTE:
            # 远程模式：连接到 VM 的 HDFS 和 YARN
            builder = (
                builder
                .config("spark.driver.bindAddress", "0.0.0.0")
                .config("spark.driver.host", "192.168.10.1")  # Windows 本机 IP
                .config("spark.hadoop.fs.defaultFS", "hdfs://hadoop100:9000")
                .config("spark.sql.warehouse.dir", "hdfs://hadoop100:9000/user/hive/warehouse")
                .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
            )
        else:
            # 本地模式
            builder = (
                builder
                .config("spark.driver.bindAddress", "127.0.0.1")
                .config("spark.hadoop.fs.defaultFS", "file:///")
                .config("spark.sql.warehouse.dir", "file:///tmp/spark-warehouse")
                .config("spark.hadoop.dfs.client.use.datanode.hostname", "true")
            )

        _spark_session = builder.getOrCreate()
        _spark_session.sparkContext.setLogLevel("WARN")
        logger.info(f"SparkSession 创建成功: {master_url}, driver.memory={SPARK_CONFIG['driver_memory']}, version={_spark_session.version}")

    return _spark_session


def stop_spark_session():
    """
    优雅关闭 SparkSession

    在 FastAPI 应用关闭时调用，释放 JVM 资源
    """
    global _spark_session

    with _spark_lock:
        if _spark_session is not None:
            logger.info("正在关闭 SparkSession...")
            try:
                _spark_session.stop()
            except Exception as e:
                logger.warning(f"关闭 SparkSession 时出错: {e}")
            finally:
                _spark_session = None
            logger.info("SparkSession 已关闭")
