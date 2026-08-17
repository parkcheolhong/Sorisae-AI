import type { OrderRecord } from '../types';

const orders: OrderRecord[] = [
  { id: 'ord-100', customer: 'metanova', total: 182000, status: 'approved' },
  { id: 'ord-101', customer: 'pilot-lab', total: 94000, status: 'queued' },
];

export function listOrders(): OrderRecord[] {
  return orders.map((order) => ({ ...order }));
}

export function findOrder(orderId: string): OrderRecord | undefined {
  return orders.find((order) => order.id === orderId);
}
