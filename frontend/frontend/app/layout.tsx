import type { Metadata } from 'next';
import Script from 'next/script';
import '../styles/globals.css';
import ClientLayout from '@/components/ui/client-layout';

export const metadata: Metadata = {
    title: '개발분석114',
    description: '마켓플레이스 · 관리자 · 오케스트레이터 통합 플랫폼',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
    return (
        <html lang="ko">
            <body>
                                <Script
                                        id="console-grammarly-noise-filter"
                                        strategy="beforeInteractive"
                                        dangerouslySetInnerHTML={{
                                                __html: `
                                                (function() {
                                                    function shouldSuppress(args) {
                                                        try {
                                                            var text = Array.prototype.map.call(args || [], function(item) {
                                                                if (typeof item === 'string') return item;
                                                                if (item && item.message) return String(item.message) + '\\n' + String(item.stack || '');
                                                                try { return JSON.stringify(item); } catch (e) { return String(item); }
                                                            }).join(' ').toLowerCase();
                                                            return text.indexOf('grammarly.js') !== -1 && text.indexOf('iterable') !== -1 && text.indexOf('not supported') !== -1;
                                                        } catch (e) {
                                                            return false;
                                                        }
                                                    }

                                                    var originalError = console.error;
                                                    var originalWarn = console.warn;

                                                    console.error = function() {
                                                        if (shouldSuppress(arguments)) return;
                                                        return originalError.apply(console, arguments);
                                                    };
                                                    console.warn = function() {
                                                        if (shouldSuppress(arguments)) return;
                                                        return originalWarn.apply(console, arguments);
                                                    };
                                                })();
                                                `,
                                        }}
                                />
                <ClientLayout>{children}</ClientLayout>
            </body>
        </html>
    );
}
