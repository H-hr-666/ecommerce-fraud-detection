"""
AI 总结综述服务模块
基于检测数据与预设模板生成智能分析报告
不依赖外部 API，纯本地规则引擎
"""

import logging
import time
from typing import Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)


def generate_summary(
    overview: Dict,
    metrics: Dict,
    feature_importance: Dict,
    top_orders: List[Dict],
    time_dist: Dict,
    device_dist: Dict,
    threshold: float = 0.8
) -> Dict:
    """
    汇总所有分析数据，生成结构化 AI 综述

    Args:
        overview: 分析概览数据
        metrics: 模型评估指标
        feature_importance: 特征重要性
        top_orders: Top 高风险订单
        time_dist: 时段分布
        device_dist: 设备分布
        threshold: 异常阈值

    Returns:
        结构化综述字典
    """
    sections = []

    # 1. 数据概览
    sections.append({
        "title": "📊 数据概览",
        "content": _summarize_overview(overview, threshold)
    })

    # 2. 模型评估
    sections.append({
        "title": "🤖 模型评估",
        "content": _summarize_models(metrics)
    })

    # 3. 特征分析
    sections.append({
        "title": "🔍 特征分析",
        "content": _summarize_features(feature_importance)
    })

    # 4. 风险发现
    sections.append({
        "title": "⚠️ 风险发现",
        "content": _summarize_risks(top_orders, time_dist, device_dist, threshold)
    })

    # 5. 建议
    sections.append({
        "title": "💡 建议",
        "content": _summarize_recommendations(overview, metrics, feature_importance, threshold)
    })

    # 一句话总结
    summary = _generate_one_line_summary(overview, metrics, threshold)

    return {
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "sections": sections,
        "summary": summary
    }


def _summarize_overview(overview: Dict, threshold: float) -> str:
    """生成数据概览段落"""
    total = overview.get("total_orders", 0)
    cleaned = overview.get("cleaned_samples", 0)
    removed = overview.get("removed_samples", 0)
    suspicious = overview.get("suspicious_orders", 0)
    ratio = overview.get("anomaly_ratio", 0)

    # 异常占比等级判断
    if ratio >= 0.15:
        level = "偏高"
        level_desc = "刷单行为较为猖獗，需立即采取治理措施"
    elif ratio >= 0.08:
        level = "中等"
        level_desc = "存在一定规模的刷单行为，建议加强监控"
    elif ratio >= 0.03:
        level = "偏低"
        level_desc = "刷单行为处于可控范围，建议持续关注"
    else:
        level = "极低"
        level_desc = "平台交易环境较为健康"

    lines = [
        f"本次分析共涵盖 **{total:,}** 笔交易订单。",
        f"经数据清洗，去除 **{removed:,}** 条缺失/异常记录，有效样本 **{cleaned:,}** 条。",
        f"以异常分数阈值 **{threshold}** 为判定标准，识别出疑似刷单订单 **{suspicious:,}** 笔，",
        f"占有效样本的 **{ratio*100:.2f}%**，异常占比处于 **{level}** 水平。",
        f"\n**判断**：{level_desc}。"
    ]
    return "\n".join(lines)


def _summarize_models(metrics: Dict) -> str:
    """生成模型评估段落"""
    if not metrics:
        return "模型尚未训练，请先点击「训练模型」按钮完成训练。"

    algorithms = {
        "isolation_forest": "孤立森林（Isolation Forest）",
        "lof": "局部离群因子（LOF）",
        "ocsvm": "单类支持向量机（One-Class SVM）"
    }

    # 找出最优模型
    best_key = None
    best_f1 = 0
    for key, m in metrics.items():
        f1 = m.get("f1", 0)
        if f1 > best_f1:
            best_f1 = f1
            best_key = key

    best_name = algorithms.get(best_key, best_key)
    best = metrics[best_key]

    # 性能对比表
    table_lines = ["| 算法 | 精确率 | 召回率 | F1 值 | 训练耗时 |", "|------|--------|--------|------|---------|"]
    for key in ["isolation_forest", "lof", "ocsvm"]:
        m = metrics.get(key, {})
        name = algorithms.get(key, key)
        p = m.get("precision", 0)
        r = m.get("recall", 0)
        f1 = m.get("f1", 0)
        t = m.get("train_time", 0)
        table_lines.append(f"| {name} | {p*100:.1f}% | {r*100:.1f}% | {f1*100:.1f}% | {t:.1f}s |")

    table = "\n".join(table_lines)

    # 训练速度对比
    times = {k: metrics[k].get("train_time", 0) for k in metrics}
    fastest_key = min(times, key=times.get)
    slowest_key = max(times, key=times.get)
    fastest_name = algorithms.get(fastest_key, fastest_key)
    slowest_name = algorithms.get(slowest_key, slowest_key)
    speed_ratio = times[slowest_key] / max(times[fastest_key], 0.01)

    lines = [
        f"三种异常检测算法已完成训练与评估，结果如下：\n",
        table,
        f"\n**最优模型**：**{best_name}** 综合表现最佳",
        f"（精确率 {best['precision']*100:.1f}%，召回率 {best['recall']*100:.1f}%，F1 {best['f1']*100:.1f}%）。",
        f"\n**训练效率**：{fastest_name} 训练最快（{times[fastest_key]:.1f}s），",
        f"{slowest_name} 最慢（{times[slowest_key]:.1f}s），",
        f"速度相差约 **{speed_ratio:.0f} 倍**。"
    ]
    return "\n".join(lines)


def _summarize_features(feature_importance: Dict) -> str:
    """生成特征分析段落"""
    if not feature_importance:
        return "特征重要性数据不可用，请先训练模型。"

    feature_names = {
        "time_diff": "下单时间间隔",
        "is_rush_hour": "凌晨下单标记",
        "log_amount": "交易金额对数",
        "device_type": "设备类型"
    }

    feature_insights = {
        "time_diff": "刷单脚本通常以极短间隔批量下单，时间间隔是最强的异常信号",
        "is_rush_hour": "凌晨 1-6 点是刷单高发时段，机器脚本不受作息限制",
        "log_amount": "刷单多选择低价商品（9.9/19.9/29.9 元），降低资金成本",
        "device_type": "刷单设备相对集中，Android 占比通常偏高"
    }

    # 按重要性排序
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)

    lines = ["基于特征与异常分数的相关性分析，各特征重要性排序如下：\n"]

    for i, (feat, score) in enumerate(sorted_features, 1):
        name = feature_names.get(feat, feat)
        insight = feature_insights.get(feat, "")
        bar = "█" * int(score * 40) + "░" * (40 - int(score * 40))
        lines.append(f"**{i}. {name}**（重要性 {score:.4f}）")
        lines.append(f"   `{bar}`")
        if insight:
            lines.append(f"   > {insight}")
        lines.append("")

    # 关键发现
    top_feature = sorted_features[0]
    top_name = feature_names.get(top_feature[0], top_feature[0])
    lines.append(f"**关键发现**：「{top_name}」是识别刷单行为的最重要特征，")
    lines.append(f"贡献了 **{top_feature[1]*100:.1f}%** 的判别权重。")

    return "\n".join(lines)


def _summarize_risks(
    top_orders: List[Dict],
    time_dist: Dict,
    device_dist: Dict,
    threshold: float
) -> str:
    """生成风险发现段落"""
    lines = []

    # 高风险订单分析
    if top_orders:
        high_risk = [o for o in top_orders if o.get("anomaly_score", 0) >= threshold]
        if high_risk:
            avg_score = np.mean([o["anomaly_score"] for o in high_risk])
            avg_amount = np.mean([o["amount"] for o in high_risk])
            avg_diff = np.mean([o["time_diff"] for o in high_risk])

            lines.append(f"**高危订单特征**（{len(high_risk)} 笔，阈值 ≥ {threshold}）：")
            lines.append(f"- 平均异常分数：**{avg_score:.4f}**")
            lines.append(f"- 平均交易金额：**¥{avg_amount:.2f}**（偏低，符合刷单低价特征）")
            lines.append(f"- 平均下单间隔：**{avg_diff:.1f} 秒**（远低于正常用户）")
            lines.append("")

    # 时段风险
    if time_dist and time_dist.get("counts"):
        counts = time_dist["counts"]
        hours = time_dist.get("hours", list(range(24)))
        rush_ratio = time_dist.get("rush_hour_ratio", 0)

        if rush_ratio > 0:
            # 找出高发时段
            rush_counts = [(h, c) for h, c in zip(hours, counts) if 1 <= h <= 6 and c > 0]
            if rush_counts:
                peak_hour = max(rush_counts, key=lambda x: x[1])
                lines.append(f"**时段风险**：凌晨 1-6 点集中了 **{rush_ratio*100:.1f}%** 的高风险订单，")
                lines.append(f"其中 **{peak_hour[0]}:00** 时段风险最高峰（{peak_hour[1]} 笔）。")
                lines.append(f"> 这一特征与机器脚本的「无人值守批量下单」行为高度吻合。")
                lines.append("")

    # 设备风险
    if device_dist and device_dist.get("devices"):
        devices = device_dist["devices"]
        counts = device_dist["counts"]
        total = sum(counts)
        if total > 0:
            top_device = devices[0]
            top_ratio = counts[0] / total
            lines.append(f"**设备风险**：高风险订单中 **{top_device}** 占比最高（{top_ratio*100:.1f}%），")
            if top_ratio > 0.5:
                lines.append(f"超过半数来自同一设备类型，存在明显的设备聚集特征。")
            else:
                lines.append(f"但设备分布相对分散，未出现极端聚集。")
            lines.append("")

    if not lines:
        lines.append("暂无足够的风险数据，请先训练模型并设置合理阈值。")

    return "\n".join(lines)


def _summarize_recommendations(
    overview: Dict,
    metrics: Dict,
    feature_importance: Dict,
    threshold: float
) -> str:
    """基于数据自动生成建议"""
    recommendations = []
    ratio = overview.get("anomaly_ratio", 0)

    # 基于异常占比
    if ratio >= 0.10:
        recommendations.append(
            "**紧急治理**：异常订单占比超过 10%，建议立即启动专项打击行动，"
            "对高风险账号进行人工复核并限制下单权限。"
        )
    elif ratio >= 0.05:
        recommendations.append(
            "**加强监控**：异常占比处于中等水平，建议将高风险订单纳入人工审核队列，"
            "重点核查凌晨时段和短间隔订单。"
        )

    # 基于特征重要性
    if feature_importance:
        sorted_feats = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
        top_feat = sorted_feats[0][0] if sorted_feats else None

        if top_feat == "time_diff":
            recommendations.append(
                "**规则引擎优化**：「下单时间间隔」是最强判别特征，建议在风控规则中"
                "对 5 秒内连续下单的行为进行自动拦截。"
            )
        elif top_feat == "is_rush_hour":
            recommendations.append(
                "**时段管控**：凌晨时段是刷单高发期，建议对 1-6 点的订单"
                "增加验证码或人工审核环节。"
            )

    # 基于模型性能
    if metrics:
        best_f1 = max(m.get("f1", 0) for m in metrics.values())
        if best_f1 >= 0.90:
            recommendations.append(
                "**模型部署**：当前模型 F1 值达到 {:.1f}%，检测精度较高，"
                "建议将模型接入生产环境的实时风控系统。".format(best_f1 * 100)
            )
        elif best_f1 >= 0.80:
            recommendations.append(
                "**持续优化**：模型性能尚可（F1 {:.1f}%），建议收集更多标注数据"
                "进行增量训练，进一步提升召回率。".format(best_f1 * 100)
            )

    # 通用建议
    recommendations.append(
        "**数据闭环**：建议将人工审核结果反馈至模型训练流程，"
        "建立「检测→审核→标注→再训练」的持续优化闭环。"
    )

    # 编号输出
    lines = []
    for i, rec in enumerate(recommendations, 1):
        lines.append(f"{i}. {rec}")
        lines.append("")

    return "\n".join(lines)


def _generate_one_line_summary(overview: Dict, metrics: Dict, threshold: float) -> str:
    """生成一句话总结"""
    total = overview.get("total_orders", 0)
    suspicious = overview.get("suspicious_orders", 0)
    ratio = overview.get("anomaly_ratio", 0)

    if not metrics:
        return f"共分析 {total:,} 笔订单，识别 {suspicious:,} 笔疑似刷单（{ratio*100:.2f}%），模型尚未训练。"

    best_f1 = max(m.get("f1", 0) for m in metrics.values())
    best_key = max(metrics, key=lambda k: metrics[k].get("f1", 0))
    best_names = {
        "isolation_forest": "孤立森林",
        "lof": "LOF",
        "ocsvm": "One-Class SVM"
    }
    best_name = best_names.get(best_key, best_key)

    return (
        f"本次扫描 {total:,} 笔交易，以阈值 {threshold} 检出 {suspicious:,} 笔疑似刷单"
        f"（占比 {ratio*100:.2f}%），最优模型 {best_name} 达到 F1={best_f1*100:.1f}%，"
        f"建议重点关注凌晨时段的短间隔低价订单。"
    )
