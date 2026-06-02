"""
工具函数模块
"""

import os
import logging
from typing import Any, Dict

def setup_logging(level: str = "INFO") -> None:
    """
    配置日志

    Args:
        level: 日志级别
    """
    logging.basicConfig(
        level=getattr(logging, level),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


def format_response(data: Any, message: str = "success", code: int = 200) -> Dict:
    """
    统一API响应格式

    Args:
        data: 响应数据
        message: 响应消息
        code: 状态码

    Returns:
        格式化的响应字典
    """
    return {
        "code": code,
        "message": message,
        "data": data
    }


def paginate_list(data: list, page: int = 1, page_size: int = 10) -> Dict:
    """
    列表分页

    Args:
        data: 数据列表
        page: 页码（从1开始）
        page_size: 每页数量

    Returns:
        分页结果字典
    """
    total = len(data)
    total_pages = (total + page_size - 1) // page_size
    start = (page - 1) * page_size
    end = start + page_size

    return {
        "items": data[start:end],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages
    }
