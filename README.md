# 电商刷单异常检测系统

基于《电商平台刷单行为的异常检测论文》开发的Python后端 + Web前端可视化平台。

## 项目简介

本项目实现了论文中提出的基于孤立森林（Isolation Forest）算法的电商刷单异常检测系统，包含：

- **算法复刻**：完整实现论文中的孤立森林、LOF、One-Class SVM三种算法
- **特征工程**：严格按论文实现4特征构造（log_amount、time_diff、is_rush_hour、device_type）
- **可视化大屏**：数据概览、模型指标、异常分布、特征重要性、嫌疑订单查询
- **交互功能**：阈值可调、模型训练、分页查询

## 技术栈

### 后端
- Python 3.9+
- FastAPI
- scikit-learn
- pandas / numpy
- uvicorn

### 前端
- HTML5 + Bootstrap 5
- ECharts 5.4
- 原生JavaScript（无需编译）

## 项目结构

```
ecommerce_fraud_detection/
├── backend/                        # 后端服务
│   ├── main.py                     # FastAPI应用入口
│   ├── config.py                   # 全局配置
│   ├── requirements.txt            # Python依赖
│   ├── data/                       # 数据目录
│   ├── models/                     # 模型存储
│   ├── services/                   # 业务服务层
│   │   ├── data_service.py         # 数据加载与清洗
│   │   ├── feature_service.py      # 特征工程
│   │   ├── model_service.py        # 模型训练与预测
│   │   └── evaluation_service.py   # 模型评估
│   ├── routers/                    # API路由层
│   │   ├── data_router.py          # 数据相关接口
│   │   ├── model_router.py         # 模型相关接口
│   │   └── analysis_router.py      # 分析结果接口
│   └── utils/                      # 工具函数
│       └── helpers.py
│
├── frontend/                       # 前端页面
│   ├── index.html                  # 主页面
│   ├── css/
│   │   └── style.css               # 自定义样式
│   └── js/
│       ├── api.js                  # API调用封装
│       ├── charts.js               # ECharts图表
│       └── app.js                  # 主逻辑
│
└── README.md                       # 项目说明
```

## 快速开始

### 1. 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

### 2. 启动后端服务

```bash
cd backend
python main.py
```

或使用uvicorn直接启动：

```bash
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. 访问系统

打开浏览器访问：**http://localhost:8000**

## API接口文档

启动服务后访问：**http://localhost:8000/docs** 查看Swagger API文档

### 核心接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/data/stats` | GET | 数据集统计信息 |
| `/api/data/distribution` | GET | 异常分数分布 |
| `/api/model/metrics` | GET | 三算法评估指标 |
| `/api/model/feature-importance` | GET | 特征重要性 |
| `/api/model/param-tuning` | GET | 参数调优AUC表 |
| `/api/model/train` | POST | 触发模型训练 |
| `/api/analysis/top-risk-orders` | GET | 高风险订单(分页) |
| `/api/analysis/overview` | GET | 分析概览 |
| `/api/analysis/threshold` | POST | 更新异常阈值 |

## 功能说明

### 1. 项目概览模块
- 总交易订单数
- 疑似刷单订单数
- 异常占比
- 模型精确率/召回率

### 2. 异常分数分布图（复刻论文图3-1）
- 直方图展示异常分数分布
- 标注0.8阈值红线

### 3. 特征重要性图（复刻论文图3-2）
- 下单时间间隔（0.45）最重要
- 凌晨下单标记（0.30）
- 交易金额对数（0.15）
- 设备类型（0.10）

### 4. 算法性能对比（复刻论文表3-3）

| 算法 | 精确率 | 召回率 | F1值 | 训练耗时 |
|------|--------|--------|------|---------|
| Isolation Forest | 93.2% | 88.7% | 90.9% | 2.1s |
| LOF | 83.1% | 79.2% | 81.1% | 128.5s |
| One-Class SVM | 85.4% | 81.5% | 83.4% | 86.3s |

### 5. 参数调优（复刻论文表3-2）
- 网格搜索：n_estimators [50, 100, 200] × max_samples [128, 256, 512]
- 最优参数：n_estimators=100, max_samples=256, AUC=0.945

### 6. 嫌疑订单查询表格
- 分页展示Top高风险订单
- 支持异常分数降序排序
- 可调阈值筛选

## 数据集

系统首次运行时会自动生成模拟数据集（38662条记录），如需使用真实数据集：

1. 从Kaggle下载电商交易数据集
2. 将CSV文件放置到 `backend/data/ecommerce_transactions.csv`
3. 确保包含字段：user_id, order_id, amount, time_diff, order_time, device_type

或通过API上传：

```bash
curl -X POST http://localhost:8000/api/data/upload -F "file=@your_dataset.csv"
```

## 论文参考

本项目严格复刻以下论文的实验结果：

- Liu F T, Ting K M, Zhou Z H. Isolation Forest [C]//2008 eighth ieee international conference on data mining. IEEE, 2008: 413-422.

## 许可证

本项目仅供学习研究使用。
