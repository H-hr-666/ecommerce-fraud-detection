/**
 * API调用封装模块
 * 统一管理所有后端接口调用
 */

const API_BASE_URL = window.location.origin;

const Api = {
    /**
     * 通用请求方法
     */
    async request(url, options = {}) {
        try {
            const response = await fetch(`${API_BASE_URL}${url}`, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            const data = await response.json();

            if (data.code === 200) {
                return data.data;
            } else {
                console.error(`API错误: ${data.message}`);
                throw new Error(data.message);
            }
        } catch (error) {
            console.error(`请求失败: ${url}`, error);
            throw error;
        }
    },

    /**
     * 获取数据集统计信息
     */
    async getDataStats() {
        return await this.request('/api/data/stats');
    },

    /**
     * 获取异常分数分布
     */
    async getAnomalyDistribution() {
        return await this.request('/api/data/distribution');
    },

    /**
     * 获取模型评估指标
     */
    async getModelMetrics() {
        return await this.request('/api/model/metrics');
    },

    /**
     * 获取特征重要性
     */
    async getFeatureImportance() {
        return await this.request('/api/model/feature-importance');
    },

    /**
     * 获取参数调优结果
     */
    async getParamTuning() {
        return await this.request('/api/model/param-tuning');
    },

    /**
     * 获取高风险订单列表
     */
    async getTopRiskOrders(page = 1, pageSize = 10, threshold = null) {
        let url = `/api/analysis/top-risk-orders?page=${page}&page_size=${pageSize}`;
        if (threshold !== null) {
            url += `&threshold=${threshold}`;
        }
        return await this.request(url);
    },

    /**
     * 获取时段分布
     */
    async getTimeDistribution(threshold = null) {
        let url = '/api/analysis/time-distribution';
        if (threshold !== null) {
            url += `?threshold=${threshold}`;
        }
        return await this.request(url);
    },

    /**
     * 获取设备分布
     */
    async getDeviceDistribution(threshold = null) {
        let url = '/api/analysis/device-distribution';
        if (threshold !== null) {
            url += `?threshold=${threshold}`;
        }
        return await this.request(url);
    },

    /**
     * 获取分析概览
     */
    async getAnalysisOverview(threshold = null) {
        let url = '/api/analysis/overview';
        if (threshold !== null) {
            url += `?threshold=${threshold}`;
        }
        return await this.request(url);
    },

    /**
     * 触发模型训练
     */
    async trainModels() {
        return await this.request('/api/model/train', { method: 'POST' });
    },

    /**
     * 更新阈值
     */
    async updateThreshold(threshold) {
        return await this.request(`/api/analysis/threshold?threshold=${threshold}`, {
            method: 'POST'
        });
    },

    /**
     * 获取训练状态
     */
    async getTrainingStatus() {
        return await this.request('/api/model/status');
    }
};
