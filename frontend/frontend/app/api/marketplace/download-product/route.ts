import { NextRequest, NextResponse } from 'next/server';
import { readdir, readFile, stat } from 'fs/promises';
import { join } from 'path';
import JSZip from 'jszip';

const EXCLUDED_SEGMENTS = new Set(['.git', '__pycache__']);

function shouldSkip(pathPart: string): boolean {
    if (!pathPart) {
        return false;
    }
    if (EXCLUDED_SEGMENTS.has(pathPart)) {
        return true;
    }
    return pathPart.endsWith('.pyc');
}

async function appendDirectoryToZip(zip: JSZip, sourceDir: string, archiveBase: string): Promise<void> {
    const entries = await readdir(sourceDir, { withFileTypes: true });
    for (const entry of entries) {
        if (shouldSkip(entry.name)) {
            continue;
        }

        const sourcePath = join(sourceDir, entry.name);
        const archivePath = `${archiveBase}/${entry.name}`;

        if (entry.isDirectory()) {
            await appendDirectoryToZip(zip, sourcePath, archivePath);
            continue;
        }

        if (!entry.isFile()) {
            continue;
        }

        const content = await readFile(sourcePath);
        zip.file(archivePath, content);
    }
}

async function findSourceDirectory(): Promise<string> {
    const cwd = process.cwd();
    const candidates = [
        process.env.PROJECT_ROOT,
        cwd,
        join(cwd, '..'),
        join(cwd, '..', '..'),
        join(cwd, '..', '..', '..'),
    ].filter((value): value is string => Boolean(value && value.trim()));

    for (const root of candidates) {
        const sourceDir = join(root, 'intraday_lgbm_live');
        try {
            const info = await stat(sourceDir);
            if (info.isDirectory()) {
                return sourceDir;
            }
        } catch {
            continue;
        }
    }

    throw new Error('intraday_lgbm_live source directory not found');
}

export async function GET(req: NextRequest) {
    const searchParams = req.nextUrl.searchParams;
    const product = searchParams.get('product');

    if (product !== 'stock-ai-autotrader') {
        return NextResponse.json({ error: 'Product not found' }, { status: 404 });
    }

    try {
        const sourceDir = await findSourceDirectory();

        // 외부 zip 바이너리 의존 없이 Node 런타임에서 직접 ZIP 생성
        const zip = new JSZip();
        await appendDirectoryToZip(zip, sourceDir, 'intraday_lgbm_live');
        const zipBuffer = await zip.generateAsync({ type: 'nodebuffer', compression: 'DEFLATE' });
        const zipBytes = new Uint8Array(zipBuffer);

        // 응답 반환
        return new NextResponse(zipBytes, {
            status: 200,
            headers: {
                'Content-Type': 'application/zip',
                'Content-Disposition': `attachment; filename="intraday_lgbm_live.zip"`,
                'Content-Length': zipBuffer.length.toString(),
            },
        });
    } catch (error) {
        console.error('ZIP 생성 오류:', error);
        return NextResponse.json(
            { error: 'Failed to create ZIP file' },
            { status: 500 }
        );
    }
}
