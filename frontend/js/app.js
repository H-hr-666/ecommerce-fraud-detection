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
    allOrders: []  // 缓存所有订单数据用于懒加载
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
    const modal = new bootstrap.Modal(document.getElementById('loadingModal'));
    modal.show();

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
        modal.hide();

        document.getElementById('statusBadge').className = 'badge bg-success me-3';
        document.getElementById('statusBadge').innerHTML = '<i class="bi bi-circle-fill"></i> 系统就绪';
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
