import { redirect } from 'next/navigation';

export default function AdminOnlyCatchAllPage() {
  redirect('/admin');
}
