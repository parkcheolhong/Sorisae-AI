import { findOrder, listOrders } from '../repositories/orderRepository';
import { readRuntimeSummary } from '../lib/runtimeStore';

export function buildHealthPayload() {
  return {
    ok: true,
    service: 'go-ops-service',
    timestamp: new Date().toISOString(),
    runtime: readRuntimeSummary(),
  };
}

export function listOperationalOrders() {
  return {
    runtime: readRuntimeSummary(),
    items: listOrders(),
  };
}

export function readOperationalOrder(orderId: string) {
  const order = findOrder(orderId);
  if (!order) {
    return null;
  }
  return {
    order,
    runtime: readRuntimeSummary(),
    nextStep: order.status === 'queued' ? 'review-and-approve' : 'handoff-ready',
  };
}
