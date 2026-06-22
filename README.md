# 电商刷单异常检测系统 v2.5.0

基于《电商平台刷单行为的异常检测论文》开发的 Python 后端 + Web 前端可视化平台，集成 Spark 大数据分析、时间序列分析、AI 智能综述与 EDA 数据探索。

## 项目简介

本系统实现了电商刷单行为的异常检测与可视化分析，包含五大核心模块：

- **sklearn 引擎**：孤立森林（Isolation Forest）、LOF、One-Class SVM 三种算法的训练、预测与评估
- **Spark 引擎**：Spark SQL 多维分析、MLlib 分布式模型训练（KMeans/GMM）、Structured Streaming 实时检测
- **时序分析引擎**：ADF 平稳性检验、ACF/PACF 分析、ARIMA/SARIMA 建模、未来 N 天预测
- **EDA 数据分析**：Jupyter Notebook 交互式数据探索，覆盖数据收集/清洗/分析/可视化全流程
- **双数据集支持**：内置电商刷单数据集（10,000 条）+ 信用卡欺诈数据集（284,807 条，Kaggle ULB）

前端提供交互式可视化大屏，支持阈值调整、模型训练、数据集上传、实时流检测、AI 智能综述等功能。

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                    前端 (HTML/JS)                        │
│  Bootstrap 5 + ECharts 5.4 + 原生 JavaScript            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌────────────┐  │
│  │ 指标概览  │ │ 图表分析  │ │ 订单查询  │ │ Spark面板  │  │
│  └──────────┘ └──────────┘ └──────────┘ └────────────┘  │
│  ┌──────────┐ ┌────────────────────┐                     │
│  │ 时序分析  │ │ AI 智能综述（弹窗） │                     │
│  └──────────┘ └────────────────────┘                     │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP API
┌────────────────────────┴────────────────────────────────┐
│                  FastAPI 服务层                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────────┐ │
│  │  data_router  │ │ model_router │ │  spark_router    │ │
│  │ 数据/分布接口 │ │ 模型/训练接口 │ │ SQL/ML/Streaming │ │
│  └──────┬───────┘ └──────┬───────┘ └────────┬─────────┘ │
│         │               │                   │           │
│  ┌──────┴───────┐ ┌──────┴───────┐ ┌────────┴─────────┐ │
│  │ data_service  │ │model_service │ │  spark_modules   │ │
│  │ 数据加载/清洗 │ │训练/预测/持久化│ │ SQL/MLlib/Stream │ │
│  └──────────────┘ └──────────────┘ └──────────────────┘ │
│  ┌──────────────┐ ┌───────────────────────────────────┐ │
│  │summary_service│ │ timeseries_service (时序分析)     │ │
│  │ (AI 综述)     │ │ ADF/ACF/PACF/ARIMA/SARIMA/预测   │ │
│  └──────────────┘ └───────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

## 技术栈

### 后端
- Python 3.9+
- FastAPI + uvicorn
- scikit-learn 1.3.2（Isolation Forest / LOF / One-Class SVM）
- PySpark 3.5.0（Spark SQL / MLlib / Structured Streaming）
- statsmodels 0.14.1（ARIMA / SARIMA / ADF 检验）
- pandas / numpy / joblib / matplotlib / seaborn

### 前端
- HTML5 + Bootstrap 5
- ECharts 5.4（10+ 种图表类型）
- 原生 JavaScript（零编译依赖）

### 数据
- 电商刷单数据集：10,000 条交易记录，95 条刷单（0.95%）
- 信用卡欺诈数据集：284,807 条交易记录（Kaggle ULB），492 条欺诈（0.17%）

### 部署环境
- **Windows 本地模式**：Spark 使用 `local[*]` 本地计算
- **VM 远程模式**：Spark 连接 `hadoop100:7077` 集群 + HDFS `hadoop100:9000`
- MySQL 数据源支持（`localhost:3306 / ecommerce_fraud`）

## 项目结构

```
ecommerce_fraud_detection/
├── backend/                            # 后端服务
│   ├── main.py                         # FastAPI 应用入口（v2.5.0）
│   ├── config.py                       # 全局配置（模型参数、Spark/MySQL 双模式配置）
│   ├── requirements.txt                # Python 依赖
│   ├── data/                           # 数据目录
│   │   ├── ecommerce_transactions.csv  # 电商刷单数据集（10,000 条）
│   │   ├── creditcard_raw.csv          # 信用卡欺诈数据集（284,807 条）
│   │   └── streaming_checkpoint/       # Spark Streaming checkpoint
│   ├── models/                         # 模型存储（sklearn pkl + Spark model）
│   ├── services/                       # 业务服务层
│   │   ├── data_service.py             # 数据加载、清洗、标签处理
│   │   ├── feature_service.py          # 特征工程（4 特征构造 + Z-Score 标准化）
│   │   ├── model_service.py            # sklearn 模型训练、预测、网格搜索
│   │   ├── evaluation_service.py       # 模型评估、指标计算、分布分析
│   │   ├── summary_service.py          # AI 智能综述生成（本地模板引擎）
│   │   └── timeseries_service.py       # 时序分析（ADF/ACF/PACF/ARIMA/SARIMA/预测）
│   ├── routers/                        # API 路由层
│   │   ├── data_router.py              # 数据统计、分布、上传接口
│   │   ├── model_router.py             # 模型训练、指标、特征重要性、参数调优
│   │   ├── analysis_router.py          # 高风险订单、时段/设备分布、阈值、AI 综述
│   │   ├── spark_router.py             # Spark SQL/MLlib/Streaming 全部接口
│   │   └── timeseries_router.py        # 时序分析 API（数据/检验/建模/预测/报告）
│   ├── spark_modules/                  # Spark 功能模块
│   │   ├── spark_session.py            # SparkSession 单例管理（Windows/VM 双模式）
│   │   ├── spark_sql_analysis.py       # Spark SQL 多维分析（6 种查询）
│   │   ├── spark_mllib_training.py     # MLlib 模型训练（KMeans + GMM）
│   │   └── spark_streaming.py          # Structured Streaming 实时检测
│   └── utils/                          # 工具函数
│       └── helpers.py                  # 日志配置、响应格式化、分页
│
├── frontend/                           # 前端页面
│   ├── index.html                      # 主页面（含 Spark 面板 + 时序分析 + AI 综述弹窗）
│   ├── css/
│   │   └── style.css                   # 自定义样式
│   └── js/
│       ├── api.js                      # API 调用封装（含 Spark/时序/AI 综述接口）
│       ├── charts.js                   # ECharts 图表（含 Spark + 时序专用图表）
│       └── app.js                      # 主逻辑（含 Spark/Streaming/时序/AI 综述）
│
├── notebooks/                          # 数据分析 Notebook
│   └── fraud_detection_eda.ipynb       # EDA 全流程：数据收集→清洗→分析→可视化
│
├── .gitignore                          # Git 忽略规则
├── LICENSE                             # MIT 许可证
└── README.md                           # 项目说明
```

## 快速开始

### 环境要求

- Python 3.9+
- Java 8/11/17（PySpark 运行依赖，需配置 `JAVA_HOME`）
- MySQL 5.7+（可选，用于数据源模式）

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 配置运行模式

编辑 `backend/config.py`：

```python
# Spark 运行模式
SPARK_USE_REMOTE = False  # True=连接VM Spark集群, False=本地local[*]模式

# MySQL 数据源（可选）
MYSQL_CONFIG = {
    "host": "localhost",
    "port": 3306,
    "user": "root",
    "password": "root",
    "database": "ecommerce_fraud",
    "table": "transactions"
}
```

### 3. 启动后端服务

```bash
cd backend
python main.py
```

或使用 uvicorn 直接启动：

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. 访问系统

打开浏览器访问：**http://localhost:8000**

- 首次访问会自动加载内置电商刷单数据集
- 点击页面右上角「训练模型」按钮，训练完成后查看全部图表
- 训练完成后自动弹出 AI 智能综述报告
- 切换到「时序分析」面板查看 90 天日级趋势和 ARIMA/SARIMA 预测
- 切换到「Spark 分析」面板体验分布式计算

### 5. 运行 EDA Notebook（可选）

```bash
cd notebooks
jupyter notebook fraud_detection_eda.ipynb
```

EDA Notebook 包含完整的双数据集分析流程：数据收集 → 清洗 → 分析 → 可视化，共 4 大章节 8 种图表。

## API 接口文档

启动服务后访问：**http://localhost:8000/docs** 查看 Swagger API 文档

### 数据接口 (`/api/data`)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/data/stats` | GET | 数据集统计信息（样本量、均值、标准差、标签分布） |
| `/api/data/distribution` | GET | 异常分数分布直方图数据 |
| `/api/data/upload` | POST | 上传自定义 CSV 数据集 |

### 模型接口 (`/api/model`)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/model/train` | POST | 触发三种模型训练 |
| `/api/model/metrics` | GET | 三算法评估指标对比 |
| `/api/model/feature-importance` | GET | 特征重要性（基于相关性分析） |
| `/api/model/param-tuning` | GET | 参数调优 AUC 对照表 |
| `/api/model/status` | GET | 模型训练状态 |

### 分析接口 (`/api/analysis`)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/analysis/overview` | GET | 分析概览（总订单、疑似数、异常占比） |
| `/api/analysis/top-risk-orders` | GET | 高风险订单列表（分页） |
| `/api/analysis/time-distribution` | GET | 高风险订单时段分布 |
| `/api/analysis/device-distribution` | GET | 高风险订单设备分布 |
| `/api/analysis/threshold` | POST | 更新异常分数阈值 |
| `/api/analysis/ai-summary` | GET | AI 智能综述报告 |

### Spark 接口 (`/api/spark`)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/spark/health` | GET | SparkSession 健康检查 |
| `/api/spark/sql/descriptive-stats` | GET | Spark SQL 描述性统计 |
| `/api/spark/sql/hourly-distribution` | GET | 每小时订单分布分析 |
| `/api/spark/sql/device-analysis` | GET | 设备类型多维分析 |
| `/api/spark/sql/user-profiling` | GET | 用户行为画像（可疑用户排序） |
| `/api/spark/sql/anomaly-segmentation` | GET | 异常分数分段分析 |
| `/api/spark/mllib/train` | POST | 训练 KMeans + GMM 模型 |
| `/api/spark/mllib/compare` | GET | Spark vs sklearn 模型对比 |
| `/api/spark/streaming/start` | POST | 启动实时流检测 |
| `/api/spark/streaming/stop` | POST | 停止实时流检测 |
| `/api/spark/streaming/status` | GET | Streaming 运行状态 |
| `/api/spark/streaming/results` | GET | 最新检测结果 |
| `/api/spark/streaming/statistics` | GET | 检测结果统计 |

### 时序分析接口 (`/api/timeseries`)

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/timeseries/data` | GET | 获取日级时序数据（90 天聚合） |
| `/api/timeseries/stationarity` | GET | ADF 平稳性检验 + ACF/PACF |
| `/api/timeseries/fit` | POST | 训练 ARIMA / SARIMA 模型 |
| `/api/timeseries/forecast` | GET | 未来 N 天预测（含 95% 置信区间） |
| `/api/timeseries/evaluate` | GET | 模型评估指标（MAE/MSE/RMSE/R²/MAPE） |
| `/api/timeseries/report` | GET | 时序分析综合报告 |

## 功能说明

### 1. 项目概览模块
- 总交易订单数、疑似刷单订单数
- 异常占比（支持阈值实时调整）
- 模型精确率 / 召回率 / F1 值

### 2. 异常分数分布图（复刻论文图 3-1）
- 直方图展示异常分数分布
- 阈值红线标注（默认 0.8，可拖拽滑块调整）

### 3. 特征重要性图（复刻论文图 3-2）
- 基于特征与异常分数的相关性分析动态计算
- 4 个特征：下单时间间隔、凌晨下单标记、交易金额对数、设备类型

### 4. 算法性能对比（复刻论文表 3-3）

| 算法 | 精确率 | 召回率 | F1 值 | 训练耗时 |
|------|--------|--------|------|---------|
| Isolation Forest | 93.2% | 88.7% | 90.9% | 2.1s |
| LOF | 83.1% | 79.2% | 81.1% | 128.5s |
| One-Class SVM | 85.4% | 81.5% | 83.4% | 86.3s |

### 5. 参数调优（复刻论文表 3-2）
- 网格搜索：n_estimators [50, 100, 200] × max_samples [128, 256, 512]
- 最优参数：n_estimators=100, max_samples=256, AUC=0.945

### 6. Spark SQL 多维分析
- **描述性统计**：均值、标准差、最值、中位数
- **时段分布**：24 小时订单量 + 平均金额双轴图
- **设备分析**：各设备类型的订单量、金额、凌晨占比
- **用户画像**：可疑用户排序（订单量大、间隔短、凌晨多）
- **异常分段**：按异常分数 5 段分布的饼图分析

### 7. Spark MLlib 模型对比
- **KMeans**：基于聚类中心距离的异常检测
- **GMM**：基于概率密度的异常检测
- 与 sklearn 三种算法的训练耗时、异常分数对比

### 8. Spark Streaming 实时检测
- Rate 源模拟订单流（可调每秒行数）
- 双模式检测：预训练 KMeans 模型（ML 模式）/ 规则引擎（回退模式）
- 实时统计：总检测数、异常数、异常率、平均分数
- 结果表格 + 分数分布图自动刷新（3 秒间隔）

### 9. 时间序列分析
- **数据转换**：将 37,000+ 条交易记录聚合为 90 天日级时序数据
- **平稳性检验**：ADF 单位根检验（原始序列 + 一阶差分）
- **自相关分析**：ACF 自相关图、PACF 偏自相关图（含 95% 置信区间）
- **双模型对比**：ARIMA(1,1,1) vs SARIMA(1,1,1)×(1,1,1,7)
- **模型评估**：MAE、MSE、RMSE、R²、MAPE 五项指标对比
- **未来预测**：支持 7/14/30 天预测，含 95% 置信区间可视化
- **分析报告**：一键生成包含数据概况、检验结果、模型对比、业务解读的完整报告

### 10. AI 智能综述
- 基于检测数据的本地模板引擎，不依赖外部 API
- 自动生成 5 段式分析报告：数据概览、模型评估、特征分析、风险发现、建议
- 触发方式：训练完成后自动弹出 + 手动点击「AI 综述」按钮

### 11. EDA 数据分析 Notebook
- Jupyter Notebook 交互式数据探索（`notebooks/fraud_detection_eda.ipynb`）
- 双数据集分析：电商刷单（10,000 条）+ 信用卡欺诈（284,807 条）
- 完整流程：数据收集 → 数据清洗（缺失值/重复值/异常值） → 数据分析（统计/维度/对比） → 数据可视化（8 种图表）
- 图表类型：标签分布饼图、金额分布直方图、特征相关性热力图、设备/时段分析柱状图、双轴折线图、箱线图、综合对比四宫格

### 12. 嫌疑订单查询表格
- 分页展示 Top 高风险订单
- 异常分数降序排序
- 风险等级标签（极高/高/中/低）

### 13. 数据集上传
- 支持拖拽或点击上传 CSV 文件
- 自动验证字段完整性（需包含 amount、time_diff）
- 上传后需重新训练模型

## 特征工程

严格按论文 2.5 节实现 4 特征构造：

| 特征 | 说明 | 构造方式 |
|------|------|---------|
| `log_amount` | 交易金额对数化 | `log(amount + 1)` |
| `time_diff` | 下单时间间隔（秒） | 原始字段 |
| `is_rush_hour` | 凌晨下单标记 | `1` if hour ∈ [1,6] else `0` |
| `device_type` | 设备类型编码 | iOS=0, Android=1, PC=2, H5=3 |

标准化方式：Z-Score（均值 0，方差 1）

## 数据集

### 内置数据集

系统内置两大真实欺诈检测数据集：

#### 电商刷单数据集

| 属性 | 值 |
|------|------|
| 文件 | `backend/data/ecommerce_transactions.csv` |
| 总记录数 | 10,000 条 |
| 刷单记录 | 95 条（`is_cheat=1`） |
| 正常记录 | 9,905 条（`is_cheat=0`） |
| 刷单比例 | 0.95% |

#### 信用卡欺诈数据集

| 属性 | 值 |
|------|------|
| 文件 | `backend/data/creditcard_raw.csv` |
| 来源 | Kaggle (ULB Machine Learning Group) |
| 总记录数 | 284,807 条 |
| 欺诈记录 | 492 条（`Class=1`） |
| 正常记录 | 284,315 条（`Class=0`） |
| 欺诈比例 | 0.17% |

### 字段说明

#### 电商刷单数据集 (`ecommerce_transactions.csv`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户编号 |
| `order_id` | string | 订单编号 |
| `amount` | float | 交易金额 |
| `time_diff` | float | 下单时间间隔（秒） |
| `order_time` | int | 下单时间（小时，0-23） |
| `device_type` | string | 设备类型（iOS/Android/PC/H5） |
| `is_cheat` | int | 刷单标签（0=正常，1=刷单） |

#### 信用卡欺诈数据集 (`creditcard_raw.csv`)

| 字段 | 类型 | 说明 |
|------|------|------|
| `Time` | float | 交易时间（距首笔交易的秒数） |
| `V1` ~ `V28` | float | PCA 降维后的 28 个匿名特征 |
| `Amount` | float | 交易金额（欧元） |
| `Class` | int | 欺诈标签（0=正常，1=欺诈） |

> **来源**：[Kaggle - Credit Card Fraud Detection](https://www.kaggle.com/mlg-ulb/creditcardfraud)，由 ULB 机器学习小组提供。V1~V28 经过 PCA 变换保护用户隐私，是信用卡欺诈检测领域的经典基准数据集。

### 使用自定义数据集

支持上传自定义 CSV 数据集：

```bash
curl -X POST http://localhost:8000/api/data/upload -F "file=@your_dataset.csv"
```

或通过前端页面拖拽上传。

## 论文参考

本项目严格复刻以下论文的实验结果：

> Liu F T, Ting K M, Zhou Z H. Isolation Forest [C]//2008 eighth ieee international conference on data mining. IEEE, 2008: 413-422.

## 版本历史

| 版本 | 日期 | 变更内容 |
|------|------|---------|
| v2.5.0 | 2026-06-22 | 新增信用卡欺诈数据集（284,807 条 Kaggle ULB）；新增 EDA 数据分析 Notebook（双数据集完整分析流程）；新增 Windows/VM 双模式 Spark 配置；新增 MySQL 数据源支持；优化 Spark MLlib 模型训练流程；完善前端 UI 和时序分析面板 |
| v2.2.0 | 2026-06-04 | 新增时间序列分析模块：ADF 平稳性检验、ACF/PACF 分析、ARIMA/SARIMA 建模、未来 7/14/30 天预测、模型评估指标对比、时序分析报告；新增 statsmodels 依赖 |
| v2.1.0 | 2026-06-03 | 替换为真实标注数据集（10,000 条，95 条刷单）；新增 `is_cheat` 标签列支持；新增 AI 智能综述功能；修复 Spark MLlib 模型覆盖写入问题；修复前端 Modal 冲突和缓存问题 |
| v2.0.0 | 2026-06-03 | 集成 Spark 大数据分析：Spark SQL 多维分析、MLlib 模型训练（KMeans/GMM）、Structured Streaming 实时检测；前端新增 Spark 分析面板；数据集拖拽上传 |
| v1.0.0 | 2026-06-02 | 初始版本：sklearn 三算法（Isolation Forest/LOF/OCSVM）训练与评估；可视化大屏；参数调优；嫌疑订单查询 |

## 许可证

本项目基于 [MIT License](LICENSE) 开源，仅供学习研究使用。

信用卡欺诈数据集（`creditcard_raw.csv`）来源于 Kaggle，遵循其原始许可协议。
