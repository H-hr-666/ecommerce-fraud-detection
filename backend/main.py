"""
FastAPI应用主入口
托管前端静态文件 + API接口服务
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import os
import logging

from config import SERVER_PORT, FRONTEND_DIR
from utils.helpers import setup_logging
from routers import data_router, model_router, analysis_router

# 配置日志
setup_logging()
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="电商刷单异常检测系统",
    description="基于孤立森林算法的电商刷单行为异常检测API服务",
    version="1.0.0"
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
                "训练模型": "/api/model/train (POST)"
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
