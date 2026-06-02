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

# 特征列名
FEATURE_COLUMNS = ["log_amount", "time_diff", "is_rush_hour", "device_type"]

# 原始数据字段
RAW_COLUMNS = ["user_id", "order_id", "amount", "time_diff", "order_time", "device_type"]

# 服务端口
SERVER_PORT = 8000
