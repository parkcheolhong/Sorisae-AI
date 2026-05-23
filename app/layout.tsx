/* FILE-ID: FILE-APP-LAYOUT-TSX */
/* SECTION-ID: SECTION-APP-LAYOUT-TSX-MAIN */
/* FEATURE-ID: FEATURE-APP-LAYOUT-TSX-RUNTIME */
/* CHUNK-ID: CHUNK-APP-LAYOUT-TSX-001 */

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang='ko'>
      <body>{children}</body>
    </html>
  );
}
