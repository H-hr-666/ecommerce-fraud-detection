"""
全局配置模块
定义项目路径、模型参数、默认阈值等配置项
"""

import os

# 项目根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 数据目录
DATA_DIR = os.path.join(BASE_DIR, "data")
DATASET_PATH = os.path.join(DATA_DIR, "ecommerce_transactions.csv")

# 模型存储目录
MODEL_DIR = os.path.join(BASE_DIR, "models")

# 前端静态文件目录
FRONTEND_DIR = os.path.join(os.path.dirname(BASE_DIR), "frontend")

# 默认模型参数（论文设定）
DEFAULT_MODEL_PARAMS = {
    "isolation_forest": {
        "n_estimators": 100,
        "max_samples": 256,
        "contamination": 0.05,
        "random_state": 42
    },
    "lof": {
        "n_neighbors": 20,
        "contamination": 0.05
    },
    "ocsvm": {
        "kernel": "rbf",
        "nu": 0.05,
        "gamma": "scale"
    }
}

# 网格搜索参数范围
GRID_SEARCH_PARAMS = {
    "n_estimators": [50, 100, 200],
    "max_samples": [128, 256, 512]
}

# 默认异常分数阈值
DEFAULT_THRESHOLD = 0.8

# MySQL 数据源配置（本地 Windows MySQL）
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "ecommerce_fraud",
    "table": "transactions"
}

# Spark 远程连接配置（VM hadoop100）
# 方案说明：跨机器 client 模式有双向通信问题，实战最佳方案是：
# Spark 计算在 Windows 本地跑（local[*]），HDFS 存储指向 VM
# 这样 PySpark 可以正常使用，VM 的 HDFS/YARN 提供完整的大数据生态展示
SPARK_REMOTE_MASTER = "spark://hadoop100:7077"
SPARK_USE_REMOTE = False  # True=连接VM Spark集群, False=本地local[*]模式
VM_HDFS = "hdfs://hadoop100:9000"  # VM HDFS 地址（供外部写入/读取）

# 特征列名
FEATURE_COLUMNS = ["log_amount", "time_diff", "is_rush_hour", "device_type"]

# 原始数据字段
RAW_COLUMNS = ["user_id", "order_id", "amount", "time_diff", "order_time", "device_type", "is_cheat"]

# 服务端口
SERVER_PORT = 8000

# Spark 配置
SPARK_CONFIG = {
    "driver_memory": "2g",
    "shuffle_partitions": 4,
    "streaming_rows_per_second": 5,
    "streaming_buffer_size": 500
}

# Streaming checkpoint 目录
SPARK_STREAMING_CHECKPOINT_DIR = os.path.join(DATA_DIR, "streaming_checkpoint")
