"""
时序分析 API 路由
提供时序数据、平稳性检验、模型训练、预测、评估接口
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from utils.helpers import format_response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/timeseries", tags=["timeseries"])

# 全局状态缓存
_ts_state = {
    "ts_df": None,
    "ts_processed": None,
    "stationarity": None,
    "acf_pacf": None,
    "arima_result": None,
    "sarima_result": None,
    "arima_forecast": None,
    "sarima_forecast": None,
    "arima_eval": None,
    "sarima_eval": None,
    "report": None
}


def _get_csv_path():
    # 使用 37,221 条完整交易数据集
    ts_csv = "/data/data/com.termux/files/home/Downloads/ecommerce_transactions.csv"
    import os
    if os.path.exists(ts_csv):
        return ts_csv
    # 回退到默认数据集
    from config import DATASET_PATH
    return DATASET_PATH


@router.get("/data")
async def get_timeseries_data():
    """
    获取时序数据（原始 + 预处理后）

    Returns:
        日级时序数据（date, daily_amount, daily_count, avg_price, rush_ratio）
    """
    try:
        from services.timeseries_service import generate_timeseries, preprocess_timeseries

        if _ts_state["ts_processed"] is not None:
            ts = _ts_state["ts_processed"]
            return format_response({
                "dates": [d.strftime("%Y-%m-%d") for d in ts.index],
                "daily_amount": [round(v, 2) for v in ts["daily_amount"].tolist()],
                "daily_count": [int(v) for v in ts["daily_count"].tolist()],
                "avg_price": [round(v, 2) for v in ts["avg_price"].tolist()],
                "rush_ratio": [round(v, 4) for v in ts["rush_ratio"].tolist()],
                "length": len(ts)
            })

        # 生成时序数据
        csv_path = _get_csv_path()
        ts_df = generate_timeseries(csv_path, n_days=90)
        ts_processed, preprocess_report = preprocess_timeseries(ts_df)

        _ts_state["ts_df"] = ts_df
        _ts_state["ts_processed"] = ts_processed

        return format_response({
            "dates": [d.strftime("%Y-%m-%d") for d in ts_processed.index],
            "daily_amount": [round(v, 2) for v in ts_processed["daily_amount"].tolist()],
            "daily_count": [int(v) for v in ts_processed["daily_count"].tolist()],
            "avg_price": [round(v, 2) for v in ts_processed["avg_price"].tolist()],
            "rush_ratio": [round(v, 4) for v in ts_processed["rush_ratio"].tolist()],
            "length": len(ts_processed),
            "preprocess": preprocess_report
        })
    except Exception as e:
        logger.error(f"获取时序数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stationarity")
async def get_stationarity():
    """
    ADF 平稳性检验 + ACF/PACF

    Returns:
        检验结果和自相关数据
    """
    try:
        from services.timeseries_service import test_stationarity, compute_acf_pacf

        # 确保时序数据已生成
        if _ts_state["ts_processed"] is None:
            await get_timeseries_data()

        ts = _ts_state["ts_processed"]
        series = ts["daily_amount"]

        # ADF 检验
        adf_result = test_stationarity(series)
        _ts_state["stationarity"] = adf_result

        # ACF/PACF
        acf_pacf = compute_acf_pacf(series, nlags=20)
        _ts_state["acf_pacf"] = acf_pacf

        # 一阶差分的 ADF 检验
        diff_series = series.diff().dropna()
        diff_adf = test_stationarity(diff_series)

        return format_response({
            "original": adf_result,
            "diff_1": diff_adf,
            "acf_pacf": acf_pacf
        })
    except Exception as e:
        logger.error(f"平稳性检验失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/fit")
async def fit_models():
    """
    训练 ARIMA 和 SARIMA 模型

    Returns:
        两个模型的训练结果
    """
    try:
        from services.timeseries_service import fit_arima, fit_sarima, evaluate_model

        # 确保时序数据已生成
        if _ts_state["ts_processed"] is None:
            await get_timeseries_data()

        ts = _ts_state["ts_processed"]
        series = ts["daily_amount"]

        # 训练 ARIMA(1,1,1)
        logger.info("训练 ARIMA(1,1,1)...")
        arima_result = fit_arima(series, order=(1, 1, 1))
        _ts_state["arima_result"] = arima_result

        # 训练 SARIMA(1,1,1)×(1,1,1,7)
        logger.info("训练 SARIMA(1,1,1)×(1,1,1,7)...")
        sarima_result = fit_sarima(series, order=(1, 1, 1), seasonal_order=(1, 1, 1, 7))
        _ts_state["sarima_result"] = sarima_result

        # 评估
        actual = series.values
        arima_eval = evaluate_model(actual, arima_result["fitted_values"])
        sarima_eval = evaluate_model(actual, sarima_result["fitted_values"])
        _ts_state["arima_eval"] = arima_eval
        _ts_state["sarima_eval"] = sarima_eval

        return format_response({
            "arima": {
                "order": arima_result["order"],
                "aic": arima_result["aic"],
                "bic": arima_result["bic"],
                "train_time": arima_result["train_time"],
                "metrics": arima_eval
            },
            "sarima": {
                "order": sarima_result["order"],
                "seasonal_order": sarima_result["seasonal_order"],
                "aic": sarima_result["aic"],
                "bic": sarima_result["bic"],
                "train_time": sarima_result["train_time"],
                "metrics": sarima_eval
            }
        }, "时序模型训练完成")
    except Exception as e:
        logger.error(f"模型训练失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/forecast")
async def get_forecast(
    steps: int = Query(default=7, ge=1, le=30, description="预测步数")
):
    """
    未来 N 期预测

    Args:
        steps: 预测天数（1-30）

    Returns:
        ARIMA 和 SARIMA 的预测结果
    """
    try:
        from services.timeseries_service import forecast_arima, forecast_sarima

        # 确保时序数据已生成
        if _ts_state["ts_processed"] is None:
            await get_timeseries_data()

        ts = _ts_state["ts_processed"]
        series = ts["daily_amount"]

        # ARIMA 预测
        arima_fc = forecast_arima(series, order=(1, 1, 1), steps=steps)
        _ts_state["arima_forecast"] = arima_fc

        # SARIMA 预测
        sarima_fc = forecast_sarima(series, order=(1, 1, 1),
                                    seasonal_order=(1, 1, 1, 7), steps=steps)
        _ts_state["sarima_forecast"] = sarima_fc

        return format_response({
            "arima": arima_fc,
            "sarima": sarima_fc
        })
    except Exception as e:
        logger.error(f"预测失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/evaluate")
async def get_evaluation():
    """
    获取模型评估指标

    Returns:
        ARIMA 和 SARIMA 的评估指标
    """
    try:
        if _ts_state["arima_eval"] is None:
            return format_response({
                "message": "请先训练模型",
                "arima": None,
                "sarima": None
            })

        return format_response({
            "arima": _ts_state["arima_eval"],
            "sarima": _ts_state["sarima_eval"]
        })
    except Exception as e:
        logger.error(f"获取评估指标失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/report")
async def get_report():
    """
    生成时序分析综合报告

    Returns:
        结构化分析报告
    """
    try:
        from services.timeseries_service import generate_timeseries_report

        # 确保所有分析已完成
        if _ts_state["ts_processed"] is None:
            await get_timeseries_data()
        if _ts_state["stationarity"] is None:
            await get_stationarity()
        if _ts_state["arima_result"] is None:
            await fit_models()
        if _ts_state["arima_forecast"] is None:
            await get_forecast(steps=7)

        report = generate_timeseries_report(
            ts_df=_ts_state["ts_processed"],
            stationarity=_ts_state["stationarity"],
            arima_result=_ts_state["arima_result"],
            sarima_result=_ts_state["sarima_result"],
            arima_eval=_ts_state["arima_eval"],
            sarima_eval=_ts_state["sarima_eval"],
            arima_forecast=_ts_state["arima_forecast"],
            sarima_forecast=_ts_state["sarima_forecast"]
        )
        _ts_state["report"] = report

        return format_response(report)
    except Exception as e:
        logger.error(f"生成报告失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))
