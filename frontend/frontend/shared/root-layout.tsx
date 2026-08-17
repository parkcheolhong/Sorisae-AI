import type { ReactNode } from 'react';

export const sharedRootMetadata = { title: '개발분석114' };

export function SharedRootLayout({ children }: { children: ReactNode }) {
  return <html lang="ko"><body>{children}</body></html>;
}
