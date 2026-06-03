"""
FastAPI应用主入口
托管前端静态文件 + API接口服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os
import logging

from config import SERVER_PORT, FRONTEND_DIR
from utils.helpers import setup_logging
from routers import data_router, model_router, analysis_router, spark_router

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app):
    """应用生命周期管理"""
    # 启动时预热 SparkSession（后台线程，不阻塞启动）
    import threading
    def _preheat_spark():
        try:
            from spark_modules.spark_session import get_spark_session
            get_spark_session()
            logger.info("SparkSession 预热完成")
        except Exception as e:
            logger.warning(f"SparkSession 预热失败（首次请求时重试）: {e}")

    preheat_thread = threading.Thread(target=_preheat_spark, daemon=True)
    preheat_thread.start()

    yield

    # 关闭时先停 Streaming，再停 SparkSession
    try:
        from spark_modules.spark_streaming import stop_streaming
        stop_result = stop_streaming()
        if stop_result.get("status") == "stopped":
            logger.info("Streaming 已在关闭时停止")
    except Exception as e:
        logger.warning(f"关闭 Streaming 时出错: {e}")

    from spark_modules.spark_session import stop_spark_session
    stop_spark_session()


# 创建FastAPI应用
app = FastAPI(
    title="电商刷单异常检测系统",
    description="基于孤立森林算法的电商刷单行为异常检测API服务",
    version="2.1.0",
    lifespan=lifespan
)

# 配置CORS跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册API路由
app.include_router(data_router.router)
app.include_router(model_router.router)
app.include_router(analysis_router.router)
app.include_router(spark_router.router)

# 托管前端静态文件
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

    @app.get("/")
    async def serve_frontend():
        """托管前端主页面"""
        index_path = os.path.join(FRONTEND_DIR, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return {"message": "前端页面不存在，请访问 /docs 查看API文档"}
else:
    @app.get("/")
    async def root():
        """API根路径"""
        return {
            "message": "电商刷单异常检测系统API",
            "docs": "/docs",
            "endpoints": {
                "数据统计": "/api/data/stats",
                "模型指标": "/api/model/metrics",
                "特征重要性": "/api/model/feature-importance",
                "参数调优": "/api/model/param-tuning",
                "高风险订单": "/api/analysis/top-risk-orders",
                "训练模型": "/api/model/train (POST)",
                "Spark分析": "/api/spark/health"
            }
        }


@app.get("/health")
async def health_check():
    """健康检查接口"""
    return {"status": "healthy", "service": "电商刷单异常检测系统"}


if __name__ == "__main__":
    logger.info(f"启动服务，端口: {SERVER_PORT}")
    logger.info(f"访问地址: http://localhost:{SERVER_PORT}")
    logger.info(f"API文档: http://localhost:{SERVER_PORT}/docs")

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=SERVER_PORT,
        reload=True
    )
