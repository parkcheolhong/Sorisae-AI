export function estimateAdminAdOrderPromptTokens(order: any): number {
    const storyboardText = JSON.stringify(order.storyboard || []);
    const productImageText = (order.product_image_prompts || []).join(' ');
    const totalChars = [
        order.title,
        order.image_prompt,
        order.background_prompt,
        order.caption_text,
        order.portrait_image_prompt,
        order.scenario_script,
        storyboardText,
        productImageText,
    ].reduce((sum, value) => sum + String(value || '').length, 0);
    return Math.ceil(totalChars / 4);
}

export function estimateAdminAdOrderRenderTokens(order: any): number {
    const durationSeconds = Math.max(1, Number(order.duration_seconds || 60));
    const cutCount = Math.max(1, Number(order.cut_count || 1));
    const qualityBonus = { standard: 60, high: 120, ultra: 180 }[String(order.render_quality || 'high') as 'standard' | 'high' | 'ultra'] || 90;
    return Math.floor((cutCount * 96) + (durationSeconds * 18) + qualityBonus);
}

export function buildFallbackAdOrderMonitorSummary(orders: any[]) {
    const statusCounter: Record<string, number> = {};
    const engineCounter: Record<string, number> = {};
    const qualityCounter: Record<string, number> = {};
    let activeOrders = 0;
    let completedOrders = 0;
    let failedOrders = 0;
    let progressSum = 0;
    let promptTokens = 0;
    let renderTokens = 0;
    let localCostTotal = 0;
    let externalCostTotal = 0;
    let storageCostTotal = 0;

    orders.forEach((order) => {
        const status = String(order.status || 'unknown');
        const engineType = String(order.engine_type || 'unknown');
        const renderQuality = String(order.render_quality || 'unknown');
        const prompt = estimateAdminAdOrderPromptTokens(order);
        const render = estimateAdminAdOrderRenderTokens(order);
        const durationSeconds = Math.max(1, Number(order.duration_seconds || 60));
        const cutCount = Math.max(1, Number(order.cut_count || 1));
        promptTokens += prompt;
        renderTokens += render;
        localCostTotal += ((durationSeconds / 60) * 0.02) + ((cutCount / 8) * 0.004);
        storageCostTotal += 0.003 + ((durationSeconds / 60) * 0.002);
        if (engineType === 'external_api' || engineType === 'dedicated_engine') {
            externalCostTotal += ((prompt / 1000) * 0.0025) + ((render / 1000) * 0.0035);
        }
        statusCounter[status] = (statusCounter[status] || 0) + 1;
        engineCounter[engineType] = (engineCounter[engineType] || 0) + 1;
        qualityCounter[renderQuality] = (qualityCounter[renderQuality] || 0) + 1;
        progressSum += Number(order.progress_percent || 0);
        if (['pending', 'queued', 'processing', 'rendering'].includes(status)) activeOrders += 1;
        if (status === 'completed') completedOrders += 1;
        if (status === 'failed') failedOrders += 1;
    });

    const totalOrders = orders.length || 1;
    const totalEstimatedCost = localCostTotal + externalCostTotal + storageCostTotal;
    const buildRatios = (counter: Record<string, number>) => Object.entries(counter)
        .sort((a, b) => b[1] - a[1])
        .map(([key, count]) => ({ key, label: key, count, ratio: Number(((count / totalOrders) * 100).toFixed(2)) }));

    return {
        totals: {
            total_orders: orders.length,
            active_orders: activeOrders,
            completed_orders: completedOrders,
            failed_orders: failedOrders,
            completion_rate: Number(((completedOrders / totalOrders) * 100).toFixed(2)),
            failure_rate: Number(((failedOrders / totalOrders) * 100).toFixed(2)),
            average_progress: Number((progressSum / totalOrders).toFixed(2)),
            average_quality_score: 0,
        },
        ratios: {
            status: buildRatios(statusCounter),
            engine: buildRatios(engineCounter),
            quality: buildRatios(qualityCounter),
        },
        token_summary: {
            estimated_prompt_tokens: promptTokens,
            estimated_render_tokens: renderTokens,
            estimated_total_tokens: promptTokens + renderTokens,
            estimated_avg_tokens_per_order: Number(((promptTokens + renderTokens) / totalOrders).toFixed(2)),
        },
        settlement: {
            local_cost_total: Number(localCostTotal.toFixed(4)),
            external_cost_total: Number(externalCostTotal.toFixed(4)),
            storage_cost_total: Number(storageCostTotal.toFixed(4)),
            total_estimated_cost: Number(totalEstimatedCost.toFixed(4)),
            estimated_cost_per_order: Number((totalEstimatedCost / totalOrders).toFixed(4)),
            settlement_line: `fallback summary · 토큰 ${(promptTokens + renderTokens).toLocaleString('ko-KR')} / 총 ${totalEstimatedCost.toFixed(2)} USD`,
        },
    };
}

export function buildFallbackAdSettlementDashboard(orders: any[]) {
    const recentLogs = orders.slice(0, 40).map((order) => {
        const promptTokens = estimateAdminAdOrderPromptTokens(order);
        const renderTokens = estimateAdminAdOrderRenderTokens(order);
        const durationSeconds = Math.max(1, Number(order.duration_seconds || 60));
        const cutCount = Math.max(1, Number(order.cut_count || 1));
        const localCost = Number((((durationSeconds / 60) * 0.02) + ((cutCount / 8) * 0.004)).toFixed(4));
        const storageCost = Number((0.003 + ((durationSeconds / 60) * 0.002)).toFixed(4));
        const externalCost = (order.engine_type === 'external_api' || order.engine_type === 'dedicated_engine')
            ? Number((((promptTokens / 1000) * 0.0025) + ((renderTokens / 1000) * 0.0035)).toFixed(4))
            : 0;
        const createdAt = order.created_at ? new Date(order.created_at) : new Date();
        const periodDay = Number.isNaN(createdAt.getTime()) ? '-' : createdAt.toISOString().slice(0, 10);
        const periodMonth = periodDay === '-' ? '-' : periodDay.slice(0, 7);
        return {
            order_id: order.id,
            user_id: order.user_id,
            status: order.status,
            engine_type: String(order.engine_type || 'unknown'),
            render_quality: String(order.render_quality || 'unknown'),
            currency: 'USD',
            prompt_tokens: promptTokens,
            render_tokens: renderTokens,
            total_tokens: promptTokens + renderTokens,
            local_cost: localCost,
            external_cost: externalCost,
            storage_cost: storageCost,
            total_cost: Number((localCost + externalCost + storageCost).toFixed(4)),
            period_day: periodDay,
            period_month: periodMonth,
            created_at: order.created_at || new Date().toISOString(),
        };
    });

    const aggregate = (items: any[], key: 'period_day' | 'period_month') => Object.values(items.reduce<Record<string, any>>((acc, item) => {
        const period = item[key];
        if (!acc[period]) acc[period] = { period, order_count: 0, total_tokens: 0, total_cost: 0 };
        acc[period].order_count += 1;
        acc[period].total_tokens += item.total_tokens;
        acc[period].total_cost = Number((acc[period].total_cost + item.total_cost).toFixed(4));
        return acc;
    }, {})).sort((a: any, b: any) => a.period.localeCompare(b.period));

    const totalTokens = recentLogs.reduce((sum, item) => sum + item.total_tokens, 0);
    const totalCost = recentLogs.reduce((sum, item) => sum + item.total_cost, 0);
    return {
        daily: aggregate(recentLogs, 'period_day').slice(-14),
        monthly: aggregate(recentLogs, 'period_month').slice(-12),
        recent_logs: recentLogs,
        settlement_line: `fallback settlement · 최근 ${recentLogs.length}건 / 토큰 ${totalTokens.toLocaleString('ko-KR')} / 총 ${totalCost.toFixed(2)} USD`,
    };
}

export function assertAdminAdOrderFallbackContract() {
    const sample = buildFallbackAdOrderMonitorSummary([]);
    if (!sample?.totals || !sample?.settlement) {
        throw new Error('admin ad order fallback contract 누락: monitor summary 핵심 필드 필요');
    }
}
