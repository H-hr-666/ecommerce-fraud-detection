/**
 * ECharts图表配置模块
 * 包含所有可视化图表的配置和渲染逻辑
 */

const Charts = {
    // 通用配色方案
    colors: {
        primary: '#2563eb',
        danger: '#dc2626',
        success: '#16a34a',
        warning: '#d97706',
        purple: '#7c3aed',
        gray: '#64748b'
    },

    /**
     * 初始化异常分数分布直方图（复刻论文图3-1）
     */
    initScoreDistributionChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.bins.map(b => b.toFixed(2)),
                name: '异常分数',
                nameLocation: 'middle',
                nameGap: 30,
                axisLabel: {
                    interval: 4,
                    rotate: 45
                }
            },
            yAxis: {
                type: 'value',
                name: '订单数量'
            },
            series: [{
                name: '订单数',
                type: 'bar',
                data: data.counts,
                itemStyle: {
                    color: function(params) {
                        // 阈值右侧标红
                        const binValue = data.bins[params.dataIndex];
                        return binValue >= data.threshold ? '#dc2626' : '#2563eb';
                    },
                    borderRadius: [2, 2, 0, 0]
                },
                markLine: {
                    silent: true,
                    symbol: 'none',
                    data: [{
                        xAxis: data.bins.findIndex(b => b >= data.threshold),
                        lineStyle: {
                            color: '#dc2626',
                            type: 'dashed',
                            width: 2
                        },
                        label: {
                            formatter: '阈值 0.8',
                            position: 'insideEndTop'
                        }
                    }]
                }
            }]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化特征重要性柱状图（复刻论文图3-2）
     */
    initFeatureImportanceChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        // 特征中文名称映射
        const featureNames = {
            'time_diff': '下单时间间隔',
            'is_rush_hour': '凌晨下单标记',
            'log_amount': '交易金额对数',
            'device_type': '设备类型'
        };

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: '{b}: {c}'
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'value',
                name: '重要性得分',
                max: 0.5
            },
            yAxis: {
                type: 'category',
                data: data.features.map(f => featureNames[f] || f),
                axisLabel: {
                    fontSize: 14
                }
            },
            series: [{
                name: '重要性',
                type: 'bar',
                data: data.importance,
                itemStyle: {
                    color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
                        { offset: 0, color: '#2563eb' },
                        { offset: 1, color: '#7c3aed' }
                    ]),
                    borderRadius: [0, 4, 4, 0]
                },
                label: {
                    show: true,
                    position: 'right',
                    formatter: '{c}',
                    fontWeight: 'bold'
                }
            }]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化算法性能对比图（复刻论文表3-3）
     */
    initAlgorithmComparisonChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {
                data: ['精确率', '召回率', 'F1值'],
                bottom: 0
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.algorithms
            },
            yAxis: {
                type: 'value',
                name: '百分比',
                max: 1,
                axisLabel: {
                    formatter: '{value}'
                }
            },
            series: [
                {
                    name: '精确率',
                    type: 'bar',
                    data: data.precision,
                    itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] }
                },
                {
                    name: '召回率',
                    type: 'bar',
                    data: data.recall,
                    itemStyle: { color: '#16a34a', borderRadius: [4, 4, 0, 0] }
                },
                {
                    name: 'F1值',
                    type: 'bar',
                    data: data.f1,
                    itemStyle: { color: '#d97706', borderRadius: [4, 4, 0, 0] }
                }
            ]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化参数调优AUC折线图（复刻论文表3-2）
     */
    initParamTuningChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        // 按n_estimators分组
        const groupedData = {};
        data.forEach(item => {
            const key = `n_estimators=${item.n_estimators}`;
            if (!groupedData[key]) {
                groupedData[key] = [];
            }
            groupedData[key].push(item);
        });

        const series = [];
        const colors = ['#2563eb', '#16a34a', '#d97706'];
        let colorIdx = 0;

        for (const [name, items] of Object.entries(groupedData)) {
            series.push({
                name: name,
                type: 'line',
                data: items.map(i => i.auc),
                smooth: true,
                symbol: 'circle',
                symbolSize: 8,
                itemStyle: { color: colors[colorIdx] },
                lineStyle: { width: 3 }
            });
            colorIdx++;
        }

        const option = {
            tooltip: {
                trigger: 'axis'
            },
            legend: {
                data: Object.keys(groupedData),
                bottom: 0
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: ['128', '256', '512'],
                name: 'max_samples',
                nameLocation: 'middle',
                nameGap: 30
            },
            yAxis: {
                type: 'value',
                name: 'AUC',
                min: 0.92,
                max: 0.96
            },
            series: series
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化时段分布图
     */
    initTimeDistributionChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.hours.map(h => `${h}:00`),
                axisLabel: {
                    interval: 2
                }
            },
            yAxis: {
                type: 'value',
                name: '订单数'
            },
            series: [{
                name: '高风险订单',
                type: 'bar',
                data: data.counts,
                itemStyle: {
                    color: function(params) {
                        // 凌晨1-6点标红
                        const hour = params.dataIndex;
                        return (hour >= 1 && hour <= 6) ? '#dc2626' : '#2563eb';
                    },
                    borderRadius: [4, 4, 0, 0]
                },
                markArea: {
                    silent: true,
                    data: [[
                        { xAxis: '1:00', itemStyle: { color: 'rgba(220,38,38,0.1)' } },
                        { xAxis: '6:00' }
                    ]]
                }
            }]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化设备分布饼图
     */
    initDeviceDistributionChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const pieData = data.devices.map((device, index) => ({
            name: device,
            value: data.counts[index]
        }));

        const option = {
            tooltip: {
                trigger: 'item',
                formatter: '{b}: {c} ({d}%)'
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                top: 'middle'
            },
            series: [{
                name: '设备类型',
                type: 'pie',
                radius: ['40%', '70%'],
                center: ['60%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    formatter: '{b}\n{d}%'
                },
                emphasis: {
                    label: {
                        show: true,
                        fontSize: 16,
                        fontWeight: 'bold'
                    }
                },
                data: pieData,
                color: ['#2563eb', '#7c3aed', '#16a34a', '#d97706']
            }]
        };

        chart.setOption(option);
        return chart;
    },

    // ==================== Spark 专用图表 ====================

    /**
     * 初始化 Spark 时段分布图
     */
    initSparkHourlyChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' },
                formatter: function(params) {
                    const hour = params[0].name;
                    const count = params[0].value;
                    const amount = params[1] ? params[1].value : '-';
                    return `${hour}<br/>订单数: ${count}<br/>平均金额: ¥${amount}`;
                }
            },
            legend: {
                data: ['订单数', '平均金额'],
                bottom: 0
            },
            grid: {
                left: '3%',
                right: '8%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.hours.map(h => `${h}:00`),
                axisLabel: { interval: 2 }
            },
            yAxis: [
                { type: 'value', name: '订单数', position: 'left' },
                { type: 'value', name: '金额(¥)', position: 'right' }
            ],
            series: [
                {
                    name: '订单数',
                    type: 'bar',
                    data: data.order_counts,
                    itemStyle: {
                        color: function(params) {
                            const hour = data.hours[params.dataIndex];
                            return (hour >= 1 && hour <= 6) ? '#dc2626' : '#2563eb';
                        },
                        borderRadius: [4, 4, 0, 0]
                    }
                },
                {
                    name: '平均金额',
                    type: 'line',
                    yAxisIndex: 1,
                    data: data.avg_amounts,
                    smooth: true,
                    symbol: 'circle',
                    symbolSize: 6,
                    itemStyle: { color: '#d97706' },
                    lineStyle: { width: 2 }
                }
            ]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化 Spark 设备分析图
     */
    initSparkDeviceChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {
                data: ['订单数', '平均金额', '凌晨占比'],
                bottom: 0
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.devices
            },
            yAxis: [
                { type: 'value', name: '数量/金额' },
                { type: 'value', name: '占比', max: 1, axisLabel: { formatter: '{value}' } }
            ],
            series: [
                {
                    name: '订单数',
                    type: 'bar',
                    data: data.order_counts,
                    itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] }
                },
                {
                    name: '平均金额',
                    type: 'bar',
                    data: data.avg_amounts,
                    itemStyle: { color: '#7c3aed', borderRadius: [4, 4, 0, 0] }
                },
                {
                    name: '凌晨占比',
                    type: 'line',
                    yAxisIndex: 1,
                    data: data.rush_hour_ratios,
                    smooth: true,
                    symbol: 'diamond',
                    symbolSize: 8,
                    itemStyle: { color: '#dc2626' },
                    lineStyle: { width: 2, type: 'dashed' }
                }
            ]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化 Spark 异常分段饼图
     */
    initSparkSegmentationChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const pieData = data.buckets.map((bucket, index) => ({
            name: bucket,
            value: data.counts[index]
        }));

        const colorMap = {
            '0-0.2': '#16a34a',
            '0.2-0.4': '#2563eb',
            '0.4-0.6': '#d97706',
            '0.6-0.8': '#dc2626',
            '0.8-1.0': '#7c3aed'
        };

        const option = {
            tooltip: {
                trigger: 'item',
                formatter: function(params) {
                    const idx = data.buckets.indexOf(params.name);
                    const avgAmount = data.avg_amounts[idx] || '-';
                    const rushRatio = data.rush_hour_ratios[idx] || '-';
                    return `${params.name}<br/>数量: ${params.value} (${params.percent}%)<br/>平均金额: ¥${avgAmount}<br/>凌晨占比: ${rushRatio}`;
                }
            },
            legend: {
                orient: 'vertical',
                left: 'left',
                top: 'middle'
            },
            series: [{
                name: '异常分段',
                type: 'pie',
                radius: ['35%', '65%'],
                center: ['60%', '50%'],
                avoidLabelOverlap: false,
                itemStyle: {
                    borderRadius: 6,
                    borderColor: '#fff',
                    borderWidth: 2
                },
                label: {
                    show: true,
                    formatter: '{b}\n{d}%'
                },
                emphasis: {
                    label: { show: true, fontSize: 14, fontWeight: 'bold' }
                },
                data: pieData,
                color: data.buckets.map(b => colorMap[b] || '#94a3b8')
            }]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化 Spark vs sklearn 对比图
     */
    initSparkComparisonChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            legend: {
                data: ['训练耗时(s)', '平均异常分', '高分占比'],
                bottom: 0
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.algorithms,
                axisLabel: { rotate: 15 }
            },
            yAxis: {
                type: 'value',
                name: '数值'
            },
            series: [
                {
                    name: '训练耗时(s)',
                    type: 'bar',
                    data: data.train_time,
                    itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] }
                },
                {
                    name: '平均异常分',
                    type: 'bar',
                    data: data.avg_anomaly_score,
                    itemStyle: { color: '#16a34a', borderRadius: [4, 4, 0, 0] }
                },
                {
                    name: '高分占比',
                    type: 'bar',
                    data: data.high_score_ratio,
                    itemStyle: { color: '#d97706', borderRadius: [4, 4, 0, 0] }
                }
            ]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 初始化 Streaming 异常分数分布图
     */
    initStreamingScoreChart(containerId, scores) {
        const chart = echarts.init(document.getElementById(containerId));

        // 构建分数区间直方图
        const bins = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0];
        const counts = new Array(bins.length - 1).fill(0);
        scores.forEach(s => {
            for (let i = 0; i < bins.length - 1; i++) {
                if (s >= bins[i] && s < bins[i + 1]) {
                    counts[i]++;
                    break;
                }
            }
        });

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: bins.slice(0, -1).map((b, i) => `${b}-${bins[i + 1]}`),
                axisLabel: { rotate: 45 }
            },
            yAxis: {
                type: 'value',
                name: '数量'
            },
            series: [{
                name: '异常分数',
                type: 'bar',
                data: counts,
                itemStyle: {
                    color: function(params) {
                        return params.dataIndex >= 5 ? '#dc2626' : '#2563eb';
                    },
                    borderRadius: [4, 4, 0, 0]
                }
            }]
        };

        chart.setOption(option);
        return chart;
    },

    // ==================== 时序分析图表 ====================

    /**
     * 时序折线图（原始数据 + 拟合值 + 预测值）
     */
    initTimeseriesChart(containerId, data) {
        const chart = echarts.init(document.getElementById(containerId));

        const series = [
            {
                name: '实际值',
                type: 'line',
                data: data.actual,
                smooth: true,
                symbol: 'circle',
                symbolSize: 4,
                itemStyle: { color: '#2563eb' },
                lineStyle: { width: 2 }
            }
        ];

        if (data.fitted_sarima) {
            series.push({
                name: 'SARIMA 拟合',
                type: 'line',
                data: data.fitted_sarima,
                smooth: true,
                symbol: 'none',
                itemStyle: { color: '#16a34a' },
                lineStyle: { width: 2, type: 'dashed' }
            });
        }

        if (data.forecast) {
            series.push({
                name: '预测值',
                type: 'line',
                data: data.forecast,
                smooth: true,
                symbol: 'diamond',
                symbolSize: 6,
                itemStyle: { color: '#dc2626' },
                lineStyle: { width: 2, type: 'dotted' }
            });
            series.push({
                name: '95% 置信上界',
                type: 'line',
                data: data.upper_bound,
                symbol: 'none',
                itemStyle: { color: 'transparent' },
                lineStyle: { width: 0 },
                areaStyle: { color: 'rgba(220,38,38,0.1)' },
                stack: 'confidence'
            });
            series.push({
                name: '95% 置信下界',
                type: 'line',
                data: data.lower_bound,
                symbol: 'none',
                itemStyle: { color: 'rgba(220,38,38,0.1)' },
                lineStyle: { width: 0 },
                areaStyle: { color: '#fff' },
                stack: 'confidence'
            });
        }

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'cross' }
            },
            legend: {
                data: series.map(s => s.name).filter(n => !n.includes('置信')),
                bottom: 0
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '15%',
                containLabel: true
            },
            xAxis: {
                type: 'category',
                data: data.dates,
                axisLabel: {
                    rotate: 45,
                    fontSize: 10,
                    formatter: function(val) {
                        return val.slice(5); // MM-DD
                    }
                }
            },
            yAxis: {
                type: 'value',
                name: '日交易额 (¥)',
                axisLabel: {
                    formatter: function(val) {
                        return (val / 1000).toFixed(0) + 'k';
                    }
                }
            },
            series: series
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * ACF/PACF 柱状图
     */
    initAcfPacfChart(containerId, data, title) {
        const chart = echarts.init(document.getElementById(containerId));

        const option = {
            tooltip: {
                trigger: 'axis',
                axisPointer: { type: 'shadow' }
            },
            grid: {
                left: '3%',
                right: '4%',
                bottom: '3%',
                top: '15%',
                containLabel: true
            },
            title: {
                text: title,
                left: 'center',
                textStyle: { fontSize: 13 }
            },
            xAxis: {
                type: 'category',
                data: data.lags.map(l => l.toString()),
                name: '滞后阶数'
            },
            yAxis: {
                type: 'value',
                name: '相关系数'
            },
            series: [
                {
                    type: 'bar',
                    data: data.values.map((v, i) => ({
                        value: v,
                        itemStyle: {
                            color: Math.abs(v) > data.conf_bound ? '#dc2626' : '#2563eb',
                            borderRadius: [2, 2, 0, 0]
                        }
                    }))
                },
                {
                    type: 'line',
                    data: data.lags.map(() => data.conf_bound),
                    symbol: 'none',
                    lineStyle: { color: '#dc2626', type: 'dashed', width: 1 },
                    name: '置信上界'
                },
                {
                    type: 'line',
                    data: data.lags.map(() => -data.conf_bound),
                    symbol: 'none',
                    lineStyle: { color: '#dc2626', type: 'dashed', width: 1 },
                    name: '置信下界'
                }
            ]
        };

        chart.setOption(option);
        return chart;
    },

    /**
     * 模型评估对比柱状图
     */
    initTsEvalChart(containerId, arimaEval, sarimaEval) {
        const chart = echarts.init(document.getElementById(containerId));

        const metrics = ['MAE', 'RMSE', 'MAPE'];
        const option = {
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            legend: { data: ['ARIMA', 'SARIMA'], bottom: 0 },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            xAxis: { type: 'category', data: metrics },
            yAxis: { type: 'value' },
            series: [
                {
                    name: 'ARIMA',
                    type: 'bar',
                    data: metrics.map(m => arimaEval[m]),
                    itemStyle: { color: '#2563eb', borderRadius: [4, 4, 0, 0] }
                },
                {
                    name: 'SARIMA',
                    type: 'bar',
                    data: metrics.map(m => sarimaEval[m]),
                    itemStyle: { color: '#16a34a', borderRadius: [4, 4, 0, 0] }
                }
            ]
        };

        chart.setOption(option);
        return chart;
    }
};
