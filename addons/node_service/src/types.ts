export interface OrderRecord {
  id: string;
  customer: string;
  total: number;
  status: 'queued' | 'approved' | 'shipped';
}
