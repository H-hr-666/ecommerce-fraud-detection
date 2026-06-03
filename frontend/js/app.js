/**
 * 主应用逻辑模块
 * 负责页面初始化、数据加载、交互控制
 */

// 全局状态
const AppState = {
    currentPage: 1,
    pageSize: 10,
    currentThreshold: 0.8,
    charts: {},
    isLoading: false,
    totalPages: 0,
    allOrders: [],  // 缓存所有订单数据用于懒加载
    // Spark 相关状态
    sparkPanelVisible: false,
    sparkHealthOk: false,
    streamingRefreshTimer: null
};

/**
 * 页面初始化
 */
document.addEventListener('DOMContentLoaded', async () => {
    console.log('页面初始化...');

    // 初始化所有图表容器
    initChartContainers();

    // 初始化拖拽上传
    initDropZone();

    // 加载所有数据
    await loadAllData();

    // 监听窗口大小变化，重绘图表
    window.addEventListener('resize', () => {
        Object.values(AppState.charts).forEach(chart => {
            if (chart && chart.resize) {
                chart.resize();
            }
        });
    });
});

/**
 * 初始化拖拽上传区域
 */
function initDropZone() {
    const dropZone = document.getElementById('dropZone');
    const fileInput = document.getElementById('fileInput');

    if (!dropZone || !fileInput) return;

    // 阻止默认拖拽行为
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // 高亮拖拽区域
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('drag-over');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('drag-over');
        }, false);
    });

    // 处理文件拖放
    dropZone.addEventListener('drop', handleDrop, false);

    // 处理文件选择
    fileInput.addEventListener('change', handleFileSelect, false);

    // 点击区域触发文件选择
    dropZone.addEventListener('click', (e) => {
        if (e.target.tagName !== 'BUTTON') {
            fileInput.click();
        }
    });
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDrop(e) {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const files = e.target.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

/**
 * 处理文件上传
 */
async function handleFile(file) {
    // 验证文件类型
    if (!file.name.endsWith('.csv')) {
        showUploadResult('请上传CSV格式文件', 'error');
        return;
    }

    // 验证文件大小（最大50MB）
    if (file.size > 50 * 1024 * 1024) {
        showUploadResult('文件大小不能超过50MB', 'error');
        return;
    }

    // 显示进度条
    const progressDiv = document.getElementById('uploadProgress');
    const resultDiv = document.getElementById('uploadResult');
    const progressBar = document.getElementById('progressBar');
    const statusText = document.getElementById('uploadStatus');

    progressDiv.style.display = 'block';
    resultDiv.style.display = 'none';
    progressBar.style.width = '0%';
    progressBar.textContent = '0%';
    statusText.textContent = '准备上传...';

    // 创建FormData
    const formData = new FormData();
    formData.append('file', file);

    try {
        // 模拟进度
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress = Math.min(progress + 10, 90);
            progressBar.style.width = progress + '%';
            progressBar.textContent = progress + '%';
            statusText.textContent = '上传中...';
        }, 200);

        // 发送请求
        const response = await fetch('/api/data/upload', {
            method: 'POST',
            body: formData
        });

        clearInterval(progressInterval);
        progressBar.style.width = '100%';
        progressBar.textContent = '100%';

        const result = await response.json();

        if (result.code === 200) {
            statusText.textContent = '上传成功！';
            showUploadResult(`
                <strong>上传成功！</strong><br>
                文件名：${result.data.filename}<br>
                数据行数：${result.data.rows.toLocaleString()}<br>
                字段：${result.data.columns.join(', ')}<br>
                <small class="text-muted">数据集已更新，请点击"训练模型"按钮重新训练</small>
            `, 'success');

            // 刷新数据统计
            setTimeout(async () => {
                await loadOverview();
            }, 1000);
        } else {
            throw new Error(result.message || '上传失败');
        }
    } catch (error) {
        statusText.textContent = '上传失败';
        progressBar.classList.add('bg-danger');
        showUploadResult(`上传失败: ${error.message}`, 'error');
    }
}

/**
 * 显示上传结果
 */
function showUploadResult(message, type) {
    const resultDiv = document.getElementById('uploadResult');
    resultDiv.style.display = 'block';
    resultDiv.className = type === 'success' ? 'upload-success' : 'upload-error';
    resultDiv.innerHTML = message;
}

/**
 * 初始化图表容器
 */
function initChartContainers() {
    const containers = [
        'scoreDistributionChart',
        'featureImportanceChart',
        'algorithmComparisonChart',
        'paramTuningChart',
        'timeDistributionChart',
        'deviceDistributionChart'
    ];

    containers.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.innerHTML = '<div class="d-flex justify-content-center align-items-center h-100"><div class="spinner-border text-primary" role="status"><span class="visually-hidden">加载中...</span></div></div>';
        }
    });
}

/**
 * 加载所有数据
 */
async function loadAllData() {
    try {
        // 并行加载所有数据
        await Promise.all([
            loadOverview(),
            loadScoreDistribution(),
            loadFeatureImportance(),
            loadAlgorithmComparison(),
            loadParamTuning(),
            loadTimeDistribution(),
            loadDeviceDistribution(),
            loadTopRiskOrders()
        ]);

        console.log('所有数据加载完成');
    } catch (error) {
        console.error('数据加载失败:', error);
    }
}

/**
 * 加载概览数据
 */
async function loadOverview() {
    try {
        const data = await Api.getAnalysisOverview(AppState.currentThreshold);

        document.getElementById('totalOrders').textContent = data.total_orders.toLocaleString();
        document.getElementById('suspiciousOrders').textContent = data.suspicious_orders.toLocaleString();
        document.getElementById('anomalyRatio').textContent = (data.anomaly_ratio * 100).toFixed(1) + '%';
        document.getElementById('modelPrecision').textContent = (data.model_metrics.precision * 100).toFixed(1) + '%';
    } catch (error) {
        console.error('加载概览数据失败:', error);
    }
}

/**
 * 加载异常分数分布
 */
async function loadScoreDistribution() {
    try {
        const data = await Api.getAnomalyDistribution();
        AppState.charts.scoreDistribution = Charts.initScoreDistributionChart('scoreDistributionChart', data);
    } catch (error) {
        console.error('加载异常分数分布失败:', error);
        showErrorChart('scoreDistributionChart');
    }
}

/**
 * 加载特征重要性
 */
async function loadFeatureImportance() {
    try {
        const data = await Api.getFeatureImportance();
        AppState.charts.featureImportance = Charts.initFeatureImportanceChart('featureImportanceChart', data);
    } catch (error) {
        console.error('加载特征重要性失败:', error);
        showErrorChart('featureImportanceChart');
    }
}

/**
 * 加载算法对比数据
 */
async function loadAlgorithmComparison() {
    try {
        const data = await Api.getModelMetrics();
        AppState.charts.algorithmComparison = Charts.initAlgorithmComparisonChart('algorithmComparisonChart', data);
    } catch (error) {
        console.error('加载算法对比数据失败:', error);
        showErrorChart('algorithmComparisonChart');
    }
}

/**
 * 加载参数调优数据
 */
async function loadParamTuning() {
    try {
        const data = await Api.getParamTuning();
        AppState.charts.paramTuning = Charts.initParamTuningChart('paramTuningChart', data);
    } catch (error) {
        console.error('加载参数调优数据失败:', error);
        showErrorChart('paramTuningChart');
    }
}

/**
 * 加载时段分布
 */
async function loadTimeDistribution() {
    try {
        const data = await Api.getTimeDistribution(AppState.currentThreshold);
        AppState.charts.timeDistribution = Charts.initTimeDistributionChart('timeDistributionChart', data);
    } catch (error) {
        console.error('加载时段分布失败:', error);
        showErrorChart('timeDistributionChart');
    }
}

/**
 * 加载设备分布
 */
async function loadDeviceDistribution() {
    try {
        const data = await Api.getDeviceDistribution(AppState.currentThreshold);
        AppState.charts.deviceDistribution = Charts.initDeviceDistributionChart('deviceDistributionChart', data);
    } catch (error) {
        console.error('加载设备分布失败:', error);
        showErrorChart('deviceDistributionChart');
    }
}

/**
 * 加载高风险订单列表（懒加载）
 * 首次加载时获取所有数据缓存，后续翻页从缓存读取
 */
async function loadTopRiskOrders() {
    try {
        // 如果缓存为空或阈值变化，重新加载数据
        if (AppState.allOrders.length === 0) {
            const data = await Api.getTopRiskOrders(1, 100, AppState.currentThreshold);
            AppState.allOrders = data.items || [];
            AppState.totalPages = Math.ceil(AppState.allOrders.length / AppState.pageSize);
        }

        // 从缓存中获取当前页数据
        const startIndex = (AppState.currentPage - 1) * AppState.pageSize;
        const endIndex = startIndex + AppState.pageSize;
        const currentPageData = AppState.allOrders.slice(startIndex, endIndex);

        // 渲染表格和分页
        renderOrdersTable(currentPageData);
        renderPagination({
            page: AppState.currentPage,
            total_pages: AppState.totalPages,
            total: AppState.allOrders.length
        });
        document.getElementById('tableCount').textContent = `${AppState.allOrders.length} 条`;
    } catch (error) {
        console.error('加载高风险订单失败:', error);
        showEmptyTable();
    }
}

/**
 * 渲染订单表格
 */
function renderOrdersTable(orders) {
    const tbody = document.getElementById('ordersTableBody');

    if (!orders || orders.length === 0) {
        tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = orders.map(order => {
        const riskLevel = getRiskLevel(order.anomaly_score);
        const rushHourText = order.is_rush_hour ? '<span class="badge bg-danger">是</span>' : '<span class="badge bg-success">否</span>';

        return `
            <tr>
                <td>${order.rank}</td>
                <td><code>${order.user_id}</code></td>
                <td><code>${order.order_id}</code></td>
                <td><strong class="text-danger">${order.anomaly_score.toFixed(4)}</strong></td>
                <td>¥${order.amount.toFixed(2)}</td>
                <td>${order.time_diff.toFixed(1)}</td>
                <td>${rushHourText}</td>
                <td>${order.device_type}</td>
                <td><span class="badge ${riskLevel.class}">${riskLevel.text}</span></td>
            </tr>
        `;
    }).join('');
}

/**
 * 渲染分页控件
 */
function renderPagination(data) {
    const pagination = document.getElementById('pagination');
    const { page, total_pages } = data;

    let html = '';

    // 上一页
    html += `
        <li class="page-item ${page <= 1 ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${page - 1})">上一页</a>
        </li>
    `;

    // 页码
    const startPage = Math.max(1, page - 2);
    const endPage = Math.min(total_pages, page + 2);

    if (startPage > 1) {
        html += '<li class="page-item"><a class="page-link" href="#" onclick="changePage(1)">1</a></li>';
        if (startPage > 2) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
    }

    for (let i = startPage; i <= endPage; i++) {
        html += `
            <li class="page-item ${i === page ? 'active' : ''}">
                <a class="page-link" href="#" onclick="changePage(${i})">${i}</a>
            </li>
        `;
    }

    if (endPage < total_pages) {
        if (endPage < total_pages - 1) {
            html += '<li class="page-item disabled"><span class="page-link">...</span></li>';
        }
        html += `<li class="page-item"><a class="page-link" href="#" onclick="changePage(${total_pages})">${total_pages}</a></li>`;
    }

    // 下一页
    html += `
        <li class="page-item ${page >= total_pages ? 'disabled' : ''}">
            <a class="page-link" href="#" onclick="changePage(${page + 1})">下一页</a>
        </li>
    `;

    pagination.innerHTML = html;
}

/**
 * 获取风险等级
 */
function getRiskLevel(score) {
    if (score >= 0.9) {
        return { class: 'bg-danger', text: '极高' };
    } else if (score >= 0.8) {
        return { class: 'bg-warning text-dark', text: '高' };
    } else if (score >= 0.6) {
        return { class: 'bg-info', text: '中' };
    } else {
        return { class: 'bg-success', text: '低' };
    }
}

/**
 * 切换页码（懒加载）
 */
function changePage(page) {
    if (page < 1 || page > AppState.totalPages) return;
    AppState.currentPage = page;

    // 从缓存加载数据
    const startIndex = (page - 1) * AppState.pageSize;
    const endIndex = startIndex + AppState.pageSize;
    const currentPageData = AppState.allOrders.slice(startIndex, endIndex);

    // 渲染当前页数据
    renderOrdersTable(currentPageData);
    renderPagination({
        page: page,
        total_pages: AppState.totalPages,
        total: AppState.allOrders.length
    });

    // 滚动到表格顶部
    document.getElementById('ordersTableBody').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

/**
 * 更新阈值显示
 */
function updateThresholdDisplay(value) {
    document.getElementById('thresholdValue').textContent = parseFloat(value).toFixed(2);
}

/**
 * 应用新阈值
 */
async function applyThreshold() {
    const slider = document.getElementById('thresholdSlider');
    const newThreshold = parseFloat(slider.value);

    try {
        await Api.updateThreshold(newThreshold);
        AppState.currentThreshold = newThreshold;
        AppState.currentPage = 1;
        AppState.allOrders = [];  // 清空缓存，重新加载

        // 刷新受影响的数据
        await Promise.all([
            loadOverview(),
            loadTopRiskOrders(),
            loadTimeDistribution(),
            loadDeviceDistribution()
        ]);

        showToast('阈值已更新', 'success');
    } catch (error) {
        console.error('更新阈值失败:', error);
        showToast('阈值更新失败', 'danger');
    }
}

/**
 * 训练模型
 */
async function trainModels() {
    if (AppState.isLoading) return;

    AppState.isLoading = true;
    const loadingModalEl = document.getElementById('loadingModal');
    const loadingModal = new bootstrap.Modal(loadingModalEl);
    loadingModal.show();

    document.getElementById('statusBadge').className = 'badge bg-warning me-3';
    document.getElementById('statusBadge').innerHTML = '<i class="bi bi-hourglass-split"></i> 训练中';

    try {
        const result = await Api.trainModels();
        console.log('训练结果:', result);

        // 清空缓存，重新加载数据
        AppState.allOrders = [];
        AppState.currentPage = 1;

        // 刷新所有数据
        await loadAllData();

        showToast('模型训练完成', 'success');
    } catch (error) {
        console.error('模型训练失败:', error);
        showToast('模型训练失败: ' + error.message, 'danger');
    } finally {
        AppState.isLoading = false;

        document.getElementById('statusBadge').className = 'badge bg-success me-3';
        document.getElementById('statusBadge').innerHTML = '<i class="bi bi-circle-fill"></i> 系统就绪';

        // 先注册关闭事件，再关闭 modal
        let aiShown = false;
        const showOnce = () => {
            if (aiShown) return;
            aiShown = true;
            showAiSummary();
        };
        loadingModalEl.addEventListener('hidden.bs.modal', showOnce, { once: true });
        loadingModal.hide();
        // 兜底：如果事件未触发，500ms 后强制弹出
        setTimeout(showOnce, 500);
    }
}

/**
 * 显示错误图表占位
 */
function showErrorChart(containerId) {
    const el = document.getElementById(containerId);
    if (el) {
        el.innerHTML = '<div class="d-flex justify-content-center align-items-center h-100 text-muted"><i class="bi bi-exclamation-circle me-2"></i>数据加载失败</div>';
    }
}

/**
 * 显示空表格
 */
function showEmptyTable() {
    const tbody = document.getElementById('ordersTableBody');
    tbody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">暂无数据，请先训练模型</td></tr>';
}

/**
 * 显示提示消息
 */
function showToast(message, type = 'info') {
    // 创建toast元素
    const toastHtml = `
        <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        </div>
    `;

    // 添加到页面
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        document.body.appendChild(toastContainer);
    }

    toastContainer.insertAdjacentHTML('beforeend', toastHtml);

    // 显示toast
    const toastEl = toastContainer.lastElementChild;
    const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
    toast.show();

    // 自动清理
    toastEl.addEventListener('hidden.bs.toast', () => {
        toastEl.remove();
    });
}

// ==================== Spark 功能函数 ====================

/**
 * 切换 Spark 面板显示/隐藏
 */
function toggleSparkPanel() {
    const panel = document.getElementById('sparkPanel');
    if (!panel) return;

    AppState.sparkPanelVisible = !AppState.sparkPanelVisible;
    panel.style.display = AppState.sparkPanelVisible ? 'block' : 'none';

    // 首次打开时检查 Spark 健康状态
    if (AppState.sparkPanelVisible && !AppState.sparkHealthOk) {
        checkSparkHealth();
    }
}

/**
 * 检查 Spark 健康状态
 */
async function checkSparkHealth() {
    try {
        const data = await Api.getSparkHealth();
        AppState.sparkHealthOk = true;
        const badge = document.getElementById('sparkStatusBadge');
        if (badge) {
            badge.className = 'badge bg-light text-dark me-2';
            badge.innerHTML = `<i class="bi bi-circle-fill text-success"></i> Spark ${data.spark_version}`;
        }
    } catch (error) {
        AppState.sparkHealthOk = false;
        const badge = document.getElementById('sparkStatusBadge');
        if (badge) {
            badge.className = 'badge bg-light text-dark me-2';
            badge.innerHTML = '<i class="bi bi-circle-fill text-danger"></i> Spark 不可用';
        }
        console.error('Spark 健康检查失败:', error);
    }
}

/**
 * 加载 Spark SQL 分析数据
 */
async function loadSparkSqlData() {
    showToast('正在加载 Spark SQL 分析数据...', 'info');

    try {
        // 并行加载所有 SQL 分析数据
        const [hourly, device, segmentation, profiling] = await Promise.all([
            Api.getSparkHourlyDistribution(),
            Api.getSparkDeviceAnalysis(),
            Api.getSparkAnomalySegmentation(),
            Api.getSparkUserProfiling(10)
        ]);

        // 渲染图表
        if (hourly) {
            AppState.charts.sparkHourly = Charts.initSparkHourlyChart('sparkHourlyChart', hourly);
        }
        if (device) {
            AppState.charts.sparkDevice = Charts.initSparkDeviceChart('sparkDeviceChart', device);
        }
        if (segmentation) {
            AppState.charts.sparkSegmentation = Charts.initSparkSegmentationChart('sparkSegmentationChart', segmentation);
        }
        if (profiling) {
            renderSparkUserProfiling(profiling);
        }

        showToast('Spark SQL 分析数据加载完成', 'success');
    } catch (error) {
        console.error('加载 Spark SQL 数据失败:', error);
        showToast('Spark SQL 数据加载失败: ' + error.message, 'danger');
    }
}

/**
 * 渲染 Spark 用户画像表格
 */
function renderSparkUserProfiling(users) {
    const tbody = document.getElementById('sparkUserProfilingBody');
    if (!tbody) return;

    if (!users || users.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">暂无数据</td></tr>';
        return;
    }

    tbody.innerHTML = users.map(user => `
        <tr>
            <td><code>${user.user_id}</code></td>
            <td>${user.order_count}</td>
            <td>¥${user.avg_amount.toFixed(2)}</td>
            <td>${user.avg_time_diff.toFixed(1)}</td>
            <td><span class="badge ${user.rush_hour_orders > 0 ? 'bg-danger' : 'bg-success'}">${user.rush_hour_orders}</span></td>
        </tr>
    `).join('');
}

/**
 * 训练 Spark MLlib 模型
 */
async function trainSparkModels() {
    if (AppState.isLoading) return;

    showToast('正在训练 Spark MLlib 模型，请稍候...', 'warning');

    try {
        const result = await Api.trainSparkModels();
        console.log('Spark 训练结果:', result);

        // 更新训练摘要
        renderSparkTrainingSummary(result);

        // 加载对比数据
        await loadSparkComparison();

        showToast('Spark MLlib 模型训练完成', 'success');
    } catch (error) {
        console.error('Spark 模型训练失败:', error);
        showToast('Spark 模型训练失败: ' + error.message, 'danger');
    }
}

/**
 * 渲染 Spark 训练结果摘要
 */
function renderSparkTrainingSummary(result) {
    const container = document.getElementById('sparkTrainingSummary');
    if (!container || !result) return;

    const kmeans = result.kmeans || {};
    const gmm = result.gmm || {};

    container.innerHTML = `
        <div class="mb-3">
            <h6 class="text-primary"><i class="bi bi-diagram-3"></i> KMeans</h6>
            <table class="table table-sm table-borderless mb-0">
                <tr><td class="text-muted">聚类数</td><td class="fw-bold">${kmeans.k || '-'}</td></tr>
                <tr><td class="text-muted">训练耗时</td><td class="fw-bold">${kmeans.train_time || '-'}s</td></tr>
                <tr><td class="text-muted">平均异常分</td><td class="fw-bold">${kmeans.avg_anomaly_score || '-'}</td></tr>
                <tr><td class="text-muted">高分占比(>0.8)</td><td class="fw-bold">${(kmeans.high_score_ratio * 100 || 0).toFixed(1)}%</td></tr>
            </table>
        </div>
        <div class="mb-3">
            <h6 class="text-success"><i class="bi bi-layers"></i> GMM</h6>
            <table class="table table-sm table-borderless mb-0">
                <tr><td class="text-muted">分量数</td><td class="fw-bold">${gmm.k || '-'}</td></tr>
                <tr><td class="text-muted">训练耗时</td><td class="fw-bold">${gmm.train_time || '-'}s</td></tr>
                <tr><td class="text-muted">平均异常分</td><td class="fw-bold">${gmm.avg_anomaly_score || '-'}</td></tr>
                <tr><td class="text-muted">高分占比(>0.8)</td><td class="fw-bold">${(gmm.high_score_ratio * 100 || 0).toFixed(1)}%</td></tr>
            </table>
        </div>
    `;
}

/**
 * 加载 Spark vs sklearn 模型对比
 */
async function loadSparkComparison() {
    try {
        const data = await Api.getSparkComparison();
        if (data && data.algorithms && data.algorithms.length > 0) {
            AppState.charts.sparkComparison = Charts.initSparkComparisonChart('sparkComparisonChart', data);
        }
    } catch (error) {
        console.error('加载 Spark 对比数据失败:', error);
    }
}

/**
 * 启动 Streaming 实时检测
 */
async function startStreaming() {
    const rowsPerSec = parseInt(document.getElementById('streamingRowsPerSec').value) || 5;

    try {
        const result = await Api.startStreaming(rowsPerSec);
        console.log('Streaming 启动:', result);

        // 更新 UI 状态
        document.getElementById('btnStartStreaming').disabled = true;
        document.getElementById('btnStopStreaming').disabled = false;
        document.getElementById('streamingStatusBadge').className = 'badge bg-success';
        document.getElementById('streamingStatusBadge').textContent = '运行中';

        const modeBadge = document.getElementById('streamingModeBadge');
        if (modeBadge) {
            modeBadge.style.display = 'inline';
            modeBadge.textContent = result.detection_mode === 'ml' ? 'ML模式(KMeans)' : '规则模式';
            modeBadge.className = result.detection_mode === 'ml' ? 'badge bg-primary' : 'badge bg-info';
        }

        showToast('实时流检测已启动', 'success');

        // 启动自动刷新
        startStreamingAutoRefresh();

    } catch (error) {
        console.error('启动 Streaming 失败:', error);
        showToast('启动失败: ' + error.message, 'danger');
    }
}

/**
 * 停止 Streaming 实时检测
 */
async function stopStreaming() {
    try {
        const result = await Api.stopStreaming();
        console.log('Streaming 停止:', result);

        // 更新 UI 状态
        document.getElementById('btnStartStreaming').disabled = false;
        document.getElementById('btnStopStreaming').disabled = true;
        document.getElementById('streamingStatusBadge').className = 'badge bg-secondary';
        document.getElementById('streamingStatusBadge').textContent = '已停止';

        showToast('实时流检测已停止', 'info');

        // 停止自动刷新
        stopStreamingAutoRefresh();

    } catch (error) {
        console.error('停止 Streaming 失败:', error);
        showToast('停止失败: ' + error.message, 'danger');
    }
}

/**
 * 启动 Streaming 自动刷新（每 3 秒）
 */
function startStreamingAutoRefresh() {
    stopStreamingAutoRefresh();
    AppState.streamingRefreshTimer = setInterval(async () => {
        await refreshStreamingResults();
        await refreshStreamingStatistics();
    }, 3000);
}

/**
 * 停止 Streaming 自动刷新
 */
function stopStreamingAutoRefresh() {
    if (AppState.streamingRefreshTimer) {
        clearInterval(AppState.streamingRefreshTimer);
        AppState.streamingRefreshTimer = null;
    }
}

/**
 * 刷新 Streaming 检测结果表格
 */
async function refreshStreamingResults() {
    try {
        const results = await Api.getStreamingResults(30);
        renderStreamingResults(results);
    } catch (error) {
        console.error('刷新 Streaming 结果失败:', error);
    }
}

/**
 * 渲染 Streaming 结果表格
 */
function renderStreamingResults(results) {
    const tbody = document.getElementById('streamingResultsBody');
    if (!tbody) return;

    if (!results || results.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" class="text-center text-muted py-3">暂无检测结果</td></tr>';
        return;
    }

    // 反转顺序，最新在前
    const reversed = [...results].reverse();

    tbody.innerHTML = reversed.map(r => {
        const statusBadge = r.is_anomaly
            ? '<span class="badge bg-danger">异常</span>'
            : '<span class="badge bg-success">正常</span>';
        const scoreClass = r.anomaly_score > 0.5 ? 'text-danger fw-bold' : '';

        return `
            <tr>
                <td><small>${r.timestamp || '-'}</small></td>
                <td><code>${r.user_id}</code></td>
                <td>¥${r.amount.toFixed(2)}</td>
                <td>${r.time_diff.toFixed(1)}</td>
                <td>${r.device_type}</td>
                <td class="${scoreClass}">${r.anomaly_score.toFixed(4)}</td>
                <td>${statusBadge}</td>
            </tr>
        `;
    }).join('');
}

/**
 * 刷新 Streaming 统计数据
 */
async function refreshStreamingStatistics() {
    try {
        const stats = await Api.getStreamingStatistics();

        document.getElementById('streamTotalCount').textContent = stats.total_count || 0;
        document.getElementById('streamAnomalyCount').textContent = stats.anomaly_count || 0;
        document.getElementById('streamAnomalyRatio').textContent = ((stats.anomaly_ratio || 0) * 100).toFixed(1) + '%';
        document.getElementById('streamAvgScore').textContent = (stats.avg_anomaly_score || 0).toFixed(3);

        // 更新分数分布图（每 10 次刷新更新一次图表）
        if (stats.total_count > 0 && stats.total_count % 50 < 5) {
            try {
                const results = await Api.getStreamingResults(200);
                const scores = results.map(r => r.anomaly_score);
                if (scores.length > 0) {
                    AppState.charts.streamingScore = Charts.initStreamingScoreChart('streamingScoreChart', scores);
                }
            } catch (e) {
                // 图表更新失败不影响主流程
            }
        }
    } catch (error) {
        console.error('刷新 Streaming 统计失败:', error);
    }
}

// ==================== AI 综述功能 ====================

/**
 * 显示 AI 综述弹窗
 */
async function showAiSummary() {
    console.log('[AI综述] 打开弹窗...');
    const modalEl = document.getElementById('aiSummaryModal');
    const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
    const body = document.getElementById('aiSummaryBody');
    const timeEl = document.getElementById('aiSummaryTime');

    // 显示加载状态
    body.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted">正在生成 AI 综述报告...</p>
        </div>
    `;
    timeEl.textContent = '';
    modal.show();

    try {
        console.log('[AI综述] 请求API...');
        const data = await Api.getAiSummary(AppState.currentThreshold);
        console.log('[AI综述] API返回成功, sections:', data?.sections?.length);
        renderAiSummary(data);
        console.log('[AI综述] 渲染完成');
    } catch (error) {
        console.error('[AI综述] 失败:', error);
        body.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-exclamation-triangle text-warning fs-1"></i>
                <p class="mt-3 text-danger">生成综述失败: ${error.message}</p>
                <p class="text-muted">请先训练模型后再生成综述</p>
                <button class="btn btn-primary btn-sm mt-2" onclick="refreshAiSummary()">
                    <i class="bi bi-arrow-clockwise"></i> 重试
                </button>
            </div>
        `;
    }
}

/**
 * 刷新 AI 综述
 */
async function refreshAiSummary() {
    const body = document.getElementById('aiSummaryBody');
    const timeEl = document.getElementById('aiSummaryTime');

    body.innerHTML = `
        <div class="text-center py-5">
            <div class="spinner-border text-primary mb-3" role="status">
                <span class="visually-hidden">Loading...</span>
            </div>
            <p class="text-muted">正在重新生成...</p>
        </div>
    `;

    try {
        const data = await Api.getAiSummary(AppState.currentThreshold);
        renderAiSummary(data);
    } catch (error) {
        console.error('[AI综述] 刷新失败:', error);
        body.innerHTML = `
            <div class="text-center py-5">
                <i class="bi bi-exclamation-triangle text-warning fs-1"></i>
                <p class="mt-3 text-danger">生成失败: ${error.message}</p>
                <button class="btn btn-primary btn-sm mt-2" onclick="refreshAiSummary()">
                    <i class="bi bi-arrow-clockwise"></i> 重试
                </button>
            </div>
        `;
    }
}

/**
 * 渲染 AI 综述内容
 */
function renderAiSummary(data) {
    const body = document.getElementById('aiSummaryBody');
    const timeEl = document.getElementById('aiSummaryTime');

    if (!data || !data.sections) {
        body.innerHTML = '<p class="text-muted text-center py-4">暂无综述数据</p>';
        return;
    }

    try {
        let html = '';

        // 一句话总结（顶部高亮）
        if (data.summary) {
            html += `
                <div class="alert alert-dark border-start border-4 border-warning mb-4" role="alert">
                    <i class="bi bi-lightbulb-fill text-warning me-2"></i>
                    <strong>总结：</strong>${escapeHtml(data.summary)}
                </div>
            `;
        }

        // 各段落
        data.sections.forEach(section => {
            html += `
                <div class="card mb-3 border-0 shadow-sm">
                    <div class="card-header bg-light fw-bold">
                        ${section.title}
                    </div>
                    <div class="card-body">
                        <div class="ai-section-content">${formatMarkdown(section.content)}</div>
                    </div>
                </div>
            `;
        });

        body.innerHTML = html;
        timeEl.textContent = `生成时间：${data.generated_at || '-'}`;
    } catch (error) {
        console.error('渲染 AI 综述失败:', error);
        // 降级：纯文本展示
        let fallback = `<p class="mb-2"><strong>${escapeHtml(data.summary || '')}</strong></p>`;
        data.sections.forEach(s => {
            fallback += `<h6 class="mt-3">${escapeHtml(s.title)}</h6>`;
            fallback += `<pre style="white-space:pre-wrap;font-size:0.85rem;">${escapeHtml(s.content)}</pre>`;
        });
        body.innerHTML = fallback;
        timeEl.textContent = `生成时间：${data.generated_at || '-'}`;
    }
}

/**
 * 简易 Markdown 转 HTML
 */
function formatMarkdown(text) {
    if (!text) return '';

    // 先处理引用块（在 escapeHtml 之前，> 不会被转义）
    let html = text;

    // 表格处理（原始文本中用 | 分隔）
    const lines = html.split('\n');
    let result = [];
    let inTable = false;
    let tableRows = [];

    for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trim();

        if (line.startsWith('|') && line.endsWith('|')) {
            if (!inTable) {
                inTable = true;
                tableRows = [];
            }
            // 跳过分隔行
            if (line.match(/^\|[\s\-|]+\|$/)) continue;
            tableRows.push(line);
        } else {
            if (inTable && tableRows.length > 0) {
                result.push(renderTable(tableRows));
                tableRows = [];
                inTable = false;
            }
            result.push(line);
        }
    }
    if (inTable && tableRows.length > 0) {
        result.push(renderTable(tableRows));
    }

    html = result.join('\n');

    // 对每行分别处理（避免跨行匹配问题）
    html = html.split('\n').map(line => {
        // 引用块（原始 > 字符）
        if (line.startsWith('> ')) {
            return `<blockquote class="blockquote ps-3 border-start border-3 border-info text-muted small">${escapeHtml(line.slice(2))}</blockquote>`;
        }
        // 加粗
        line = line.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
        // 代码
        line = line.replace(/`([^`]+)`/g, '<code class="bg-light px-1 rounded">$1</code>');
        // 对非标签内容做 HTML 转义（保留已生成的 HTML 标签）
        return line;
    }).join('\n');

    // 换行转 <br>
    html = html.replace(/\n/g, '<br>');
    // 清理标签间的多余 <br>
    html = html.replace(/<br>\s*(<\/?(div|table|thead|tbody|tr|blockquote|strong|code))/g, '$1');
    html = html.replace(/(<\/(div|table|thead|tbody|tr|blockquote|strong|code)>)\s*<br>/g, '$1');
    // 清理连续 <br>
    html = html.replace(/(<br>){3,}/g, '<br><br>');

    return html;
}

/**
 * 渲染简易表格
 */
function renderTable(rows) {
    if (rows.length === 0) return '';

    let html = '<div class="table-responsive"><table class="table table-sm table-bordered mt-2 mb-2">';

    rows.forEach((row, idx) => {
        const cells = row.split('|').filter(c => c.trim() !== '');
        const tag = idx === 0 ? 'th' : 'td';
        const cls = idx === 0 ? ' class="table-dark"' : '';
        html += `<tr${cls}>`;
        cells.forEach(cell => {
            html += `<${tag}>${cell.trim()}</${tag}>`;
        });
        html += '</tr>';
    });

    html += '</table></div>';
    return html;
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
