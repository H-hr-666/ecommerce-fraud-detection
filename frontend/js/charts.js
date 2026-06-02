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
    }
};
