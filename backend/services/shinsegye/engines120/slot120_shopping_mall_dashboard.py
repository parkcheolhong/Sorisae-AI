#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🛒 자율 쇼핑몰 시각화 대시보드
실시간 쇼핑몰 운영 현황을 웹에서 시각적으로 확인할 수 있는 대시보드
"""

import os
import threading
import time
import webbrowser

from flask import Flask, jsonify, render_template

from modules.ai_code_manager.autonomous_marketing_system import AutonomousMarketingSystem
from modules.ai_code_manager.autonomous_shopping_mall import AutonomousShoppingMall

app = Flask(__name__)

# 전역 변수
shopping_mall = None
marketing_system = None
dashboard_data = {
    "mall_status": {},
    "products": [],
    "sales_data": [],
    "marketing_campaigns": [],
    "analytics": {}
}


def initialize_systems():
    """시스템 초기화"""
    global shopping_mall, marketing_system
    shopping_mall = AutonomousShoppingMall()
    marketing_system = AutonomousMarketingSystem()


def update_dashboard_data():
    """대시보드 데이터 주기적 업데이트"""
    global dashboard_data, shopping_mall, marketing_system

    while True:
        try:
            if shopping_mall and marketing_system:
                # 쇼핑몰 현황 업데이트
                mall_cycle = shopping_mall.run_autonomous_cycle()
                dashboard_data["mall_status"] = mall_cycle

                # 상품 데이터 업데이트
                if hasattr(shopping_mall, 'products') and shopping_mall.products:
                    dashboard_data["products"] = shopping_mall.products[-10:]  # 최근 10개

                # 마케팅 데이터 업데이트
                marketing_system.run_autonomous_marketing_cycle()
                dashboard_data["marketing_campaigns"] = marketing_system.ad_campaigns[-5:]  # 최근 5개

                # 분석 데이터 업데이트
                analytics = marketing_system.generate_sales_analytics_report()
                dashboard_data["analytics"] = analytics

        except Exception as e:
            print(f"대시보드 업데이트 오류: {e}")

        time.sleep(10)  # 10초마다 업데이트


@app.route('/')
def dashboard():
    """메인 대시보드 페이지"""
    return render_template('dashboard.html')


@app.route('/api/dashboard-data')
def get_dashboard_data():
    """대시보드 데이터 API"""
    return jsonify(dashboard_data)


@app.route('/api/mall-status')
def get_mall_status():
    """쇼핑몰 현황 API"""
    if shopping_mall:
        status = shopping_mall.run_autonomous_cycle()
        return jsonify(status)
    return jsonify({"error": "쇼핑몰 시스템 미초기화"})


@app.route('/api/products')
def get_products():
    """상품 목록 API"""
    if shopping_mall and hasattr(shopping_mall, 'products'):
        return jsonify(shopping_mall.products[-20:])  # 최근 20개
    return jsonify([])


@app.route('/api/marketing-campaigns')
def get_marketing_campaigns():
    """마케팅 캠페인 API"""
    if marketing_system:
        return jsonify(marketing_system.ad_campaigns[-10:])  # 최근 10개
    return jsonify([])


@app.route('/api/analytics')
def get_analytics():
    """분석 데이터 API"""
    if marketing_system:
        analytics = marketing_system.generate_sales_analytics_report()
        return jsonify(analytics)
    return jsonify({})


@app.route('/api/start-mall')
def start_mall():
    """쇼핑몰 시작 API"""
    if shopping_mall:
        result = shopping_mall.run_autonomous_cycle()
        return jsonify({"status": "success", "data": result})
    return jsonify({"status": "error", "message": "쇼핑몰 시스템 미초기화"})


@app.route('/api/start-marketing')
def start_marketing():
    """마케팅 시작 API"""
    if marketing_system:
        result = marketing_system.run_autonomous_marketing_cycle()
        return jsonify({"status": "success", "data": result})
    return jsonify({"status": "error", "message": "마케팅 시스템 미초기화"})


def create_dashboard_template():
    """대시보드 HTML 템플릿 생성"""
    template_dir = "templates"
    os.makedirs(template_dir, exist_ok=True)

    html_content = '''
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🛒 자율 쇼핑몰 대시보드</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #333;
            min-height: 100vh;
        }

        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px;
            text-align: center;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }

        .header h1 {
            font-size: 2.5em;
            color: #4a5568;
            margin-bottom: 10px;
        }

        .header .subtitle {
            color: #718096;
            font-size: 1.2em;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 20px;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }

        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.1);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }

        .card:hover {
            transform: translateY(-5px);
        }

        .card-header {
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #e2e8f0;
        }

        .card-icon {
            font-size: 2em;
            margin-right: 15px;
        }

        .card-title {
            font-size: 1.4em;
            font-weight: bold;
            color: #2d3748;
        }

        .metric {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #f7fafc;
        }

        .metric:last-child {
            border-bottom: none;
        }

        .metric-label {
            color: #4a5568;
            font-weight: 500;
        }

        .metric-value {
            font-weight: bold;
            color: #2b6cb0;
            font-size: 1.1em;
        }

        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }

        .status-active { background-color: #48bb78; }
        .status-warning { background-color: #ed8936; }
        .status-error { background-color: #f56565; }

        .control-panel {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 25px;
            text-align: center;
            margin-bottom: 30px;
        }

        .btn {
            background: linear-gradient(135deg, #4299e1, #3182ce);
            color: white;
            border: none;
            padding: 12px 30px;
            border-radius: 25px;
            font-size: 1.1em;
            font-weight: bold;
            cursor: pointer;
            margin: 0 10px;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(66, 153, 225, 0.4);
        }

        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(66, 153, 225, 0.6);
        }

        .btn.success {
            background: linear-gradient(135deg, #48bb78, #38a169);
        }

        .btn.warning {
            background: linear-gradient(135deg, #ed8936, #dd6b20);
        }

        .products-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 15px;
        }

        .product-card {
            background: #f7fafc;
            border-radius: 10px;
            padding: 15px;
            border-left: 4px solid #4299e1;
        }

        .product-name {
            font-weight: bold;
            color: #2d3748;
            margin-bottom: 8px;
        }

        .product-price {
            color: #38a169;
            font-size: 1.2em;
            font-weight: bold;
        }

        .loading {
            text-align: center;
            color: #718096;
            font-style: italic;
        }

        .chart-container {
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f7fafc;
            border-radius: 10px;
            margin-top: 20px;
        }

        .auto-refresh {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(255, 255, 255, 0.9);
            padding: 10px 15px;
            border-radius: 20px;
            font-size: 0.9em;
            color: #4a5568;
        }

        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }

        .pulse {
            animation: pulse 2s infinite;
        }
    </style>
</head>
<body>
    <div class="auto-refresh">
        🔄 자동 새로고침: <span id="refresh-timer">10</span>초
    </div>

    <div class="header">
        <h1>🛒 자율 쇼핑몰 대시보드</h1>
        <p class="subtitle">실시간 AI 비즈니스 모니터링 시스템</p>
    </div>

    <div class="container">
        <!-- 제어 패널 -->
        <div class="control-panel">
            <h3 style="margin-bottom: 20px;">🎮 제어 패널</h3>
            <button class="btn success" onclick="startMall()">🛒 쇼핑몰 시작</button>
            <button class="btn warning" onclick="startMarketing()">🎯 마케팅 시작</button>
            <button class="btn" onclick="refreshData()">🔄 데이터 새로고침</button>
        </div>

        <!-- 주요 지표 -->
        <div class="dashboard-grid">
            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🛒</span>
                    <span class="card-title">쇼핑몰 현황</span>
                </div>
                <div id="mall-status">
                    <div class="loading">데이터 로딩 중...</div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-icon">🎯</span>
                    <span class="card-title">마케팅 현황</span>
                </div>
                <div id="marketing-status">
                    <div class="loading">데이터 로딩 중...</div>
                </div>
            </div>

            <div class="card">
                <div class="card-header">
                    <span class="card-icon">📊</span>
                    <span class="card-title">수익 분석</span>
                </div>
                <div id="analytics-status">
                    <div class="loading">데이터 로딩 중...</div>
                </div>
            </div>
        </div>

        <!-- 상품 목록 -->
        <div class="card">
            <div class="card-header">
                <span class="card-icon">📦</span>
                <span class="card-title">최신 상품</span>
            </div>
            <div id="products-list">
                <div class="loading">상품 로딩 중...</div>
            </div>
        </div>
    </div>

    <script>
        let refreshTimer = 10;
        let refreshInterval;

        // 페이지 로드 시 초기화
        window.onload = function() {
            refreshData();
            startRefreshTimer();
        };

        // 자동 새로고침 타이머
        function startRefreshTimer() {
            refreshInterval = setInterval(() => {
                refreshTimer--;
                document.getElementById('refresh-timer').textContent = refreshTimer;

                if (refreshTimer <= 0) {
                    refreshData();
                    refreshTimer = 10;
                }
            }, 1000);
        }

        // 데이터 새로고침
        async function refreshData() {
            try {
                const response = await fetch('/api/dashboard-data');
                const data = await response.json();

                updateMallStatus(data.mall_status);
                updateMarketingStatus(data.marketing_campaigns);
                updateAnalytics(data.analytics);
                updateProducts(data.products);

                refreshTimer = 10;
            } catch (error) {
                console.error('데이터 로드 실패:', error);
            }
        }

        // 쇼핑몰 현황 업데이트
        function updateMallStatus(status) {
            const container = document.getElementById('mall-status');
            if (!status || Object.keys(status).length === 0) {
                container.innerHTML = '<div class="loading">쇼핑몰 데이터 없음</div>';
                return;
            }

            container.innerHTML = `
                <div class="metric">
                    <span class="metric-label">🆕 신제품</span>
                    <span class="metric-value">${status.new_products || 0}개</span>
                </div>
                <div class="metric">
                    <span class="metric-label">💰 판매건수</span>
                    <span class="metric-value">${status.sales_made || 0}건</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🤖 자동구매</span>
                    <span class="metric-value">${status.purchases_made || 0}건</span>
                </div>
                <div class="metric">
                    <span class="metric-label">💵 총 수익</span>
                    <span class="metric-value">${(status.total_revenue || 0).toLocaleString()}원</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🎯 상태</span>
                    <span class="metric-value">
                        <span class="status-indicator status-active"></span>
                        자율 운영 중
                    </span>
                </div>
            `;
        }

        // 마케팅 현황 업데이트
        function updateMarketingStatus(campaigns) {
            const container = document.getElementById('marketing-status');
            if (!campaigns || campaigns.length === 0) {
                container.innerHTML = '<div class="loading">마케팅 데이터 없음</div>';
                return;
            }

            const totalCampaigns = campaigns.length;
            const activeCampaigns = campaigns.filter(c => c.status === '활성').length;
            const totalCost = campaigns.reduce((sum, c) => sum + (c.performance_metrics?.cost || 0), 0);
            const totalRevenue = campaigns.reduce((sum, c) => sum + (c.performance_metrics?.revenue || 0), 0);
            const avgRoi = totalCost > 0 ? (totalRevenue / totalCost) : 0;

            container.innerHTML = `
                <div class="metric">
                    <span class="metric-label">📊 총 캠페인</span>
                    <span class="metric-value">${totalCampaigns}개</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🟢 활성 캠페인</span>
                    <span class="metric-value">${activeCampaigns}개</span>
                </div>
                <div class="metric">
                    <span class="metric-label">💸 투자 비용</span>
                    <span class="metric-value">${totalCost.toLocaleString()}원</span>
                </div>
                <div class="metric">
                    <span class="metric-label">💰 창출 수익</span>
                    <span class="metric-value">${totalRevenue.toLocaleString()}원</span>
                </div>
                <div class="metric">
                    <span class="metric-label">📈 평균 ROI</span>
                    <span class="metric-value">${avgRoi.toFixed(2)}배</span>
                </div>
            `;
        }

        // 분석 데이터 업데이트
        function updateAnalytics(analytics) {
            const container = document.getElementById('analytics-status');
            if (!analytics || !analytics.summary) {
                container.innerHTML = '<div class="loading">분석 데이터 없음</div>';
                return;
            }

            const summary = analytics.summary;

            container.innerHTML = `
                <div class="metric">
                    <span class="metric-label">📊 전체 ROI</span>
                    <span class="metric-value">${summary.overall_roi || 0}배</span>
                </div>
                <div class="metric">
                    <span class="metric-label">💰 총 수익</span>
                    <span class="metric-value">${(summary.total_revenue || 0).toLocaleString()}원</span>
                </div>
                <div class="metric">
                    <span class="metric-label">💎 순이익</span>
                    <span class="metric-value">${(summary.profit || 0).toLocaleString()}원</span>
                </div>
                <div class="metric">
                    <span class="metric-label">🎯 전환수</span>
                    <span class="metric-value">${(summary.total_conversions || 0).toLocaleString()}건</span>
                </div>
            `;
        }

        // 상품 목록 업데이트
        function updateProducts(products) {
            const container = document.getElementById('products-list');
            if (!products || products.length === 0) {
                container.innerHTML = '<div class="loading">상품 데이터 없음</div>';
                return;
            }

            let html = '<div class="products-grid">';
            products.slice(0, 8).forEach(product => {
                html += `
                    <div class="product-card">
                        <div class="product-name">${product.name || '상품명'}</div>
                        <div class="product-price">${(product.price || 0).toLocaleString()}원</div>
                        <div style="margin-top: 8px; color: #718096; font-size: 0.9em;">
                            카테고리: ${product.category || '기타'}
                        </div>
                    </div>
                `;
            });
            html += '</div>';

            container.innerHTML = html;
        }

        // 쇼핑몰 시작
        async function startMall() {
            try {
                const response = await fetch('/api/start-mall');
                const result = await response.json();

                if (result.status === 'success') {
                    alert('🛒 쇼핑몰이 성공적으로 시작되었습니다!');
                    refreshData();
                } else {
                    alert('❌ 쇼핑몰 시작 실패: ' + result.message);
                }
            } catch (error) {
                alert('❌ 오류 발생: ' + error.message);
            }
        }

        // 마케팅 시작
        async function startMarketing() {
            try {
                const response = await fetch('/api/start-marketing');
                const result = await response.json();

                if (result.status === 'success') {
                    alert('🎯 마케팅이 성공적으로 시작되었습니다!');
                    refreshData();
                } else {
                    alert('❌ 마케팅 시작 실패: ' + result.message);
                }
            } catch (error) {
                alert('❌ 오류 발생: ' + error.message);
            }
        }
    </script>
</body>
</html>
    '''

    with open(os.path.join(template_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)


def start_dashboard_server():
    """대시보드 서버 시작"""
    print("🌐 쇼핑몰 대시보드 서버 시작 중...")

    # 템플릿 생성
    create_dashboard_template()

    # 시스템 초기화
    initialize_systems()

    # 백그라운드 데이터 업데이트 시작
    update_thread = threading.Thread(target=update_dashboard_data, daemon=True)
    update_thread.start()

    print("✅ 대시보드 준비 완료!")
    print("🔗 브라우저에서 http://localhost:5050 을 열어주세요")

    # 자동으로 브라우저 열기
    threading.Timer(2.0, lambda: webbrowser.open('http://localhost:5050')).start()

    # Flask 서버 시작
    app.run(host='0.0.0.0', port=5050, debug=False)


if __name__ == "__main__":
    start_dashboard_server()
