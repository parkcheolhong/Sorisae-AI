interface QuantCompareRowLike {
    grade: string;
    model: string;
    status: string;
    elapsedSeconds: number | null;
    responseChars: number | null;
    gpuUtilMax: number | null;
    gpuUtilAvg: number | null;
    gpuVramMaxMib: number | null;
}

interface QuantCompareSummaryLike {
    path: string;
    reportDate: string;
    prompt: string;
    maxTokens: string;
    rows: QuantCompareRowLike[];
    previewLines: string[];
    issues: string[];
}

interface AdminWorkspaceTextEntryLike {
    name: string;
    path: string;
    kind: 'dir' | 'file';
    modified_at?: number | null;
}

interface AdminWorkspaceTextListingLike {
    entries: AdminWorkspaceTextEntryLike[];
}

interface AdminWorkspaceTextFileResponseLike {
    path: string;
    content: string;
}

const parseNullableNumber = (value: string) => {
    const trimmed = value.trim();
    if (!trimmed || trimmed === '-' || trimmed.toLowerCase() === 'n/a') {
        return null;
    }
    const parsed = Number(trimmed);
    return Number.isFinite(parsed) ? parsed : null;
};

export const parseQuantCompareReport = (
    reportPath: string,
    content: string,
): QuantCompareSummaryLike => {
    const lines = content.split(/\r?\n/);
    const rows: QuantCompareRowLike[] = [];
    const previewLines: string[] = [];
    const issues: string[] = [];
    let reportDate = '';
    let prompt = '';
    let maxTokens = '';
    let section: 'table' | 'preview' | 'issues' | null = null;

    for (const rawLine of lines) {
        const line = rawLine.trim();
        if (!line) {
            if (section !== 'table') {
                section = null;
            }
            continue;
        }
        if (line.startsWith('- Date:')) {
            reportDate = line.replace('- Date:', '').trim();
            continue;
        }
        if (line.startsWith('- Prompt:')) {
            prompt = line.replace('- Prompt:', '').trim();
            continue;
        }
        if (line.startsWith('- max_tokens:')) {
            maxTokens = line.replace('- max_tokens:', '').trim();
            continue;
        }
        if (line === '## Response Preview') {
            section = 'preview';
            continue;
        }
        if (line === '## Issues') {
            section = 'issues';
            continue;
        }
        if (line.startsWith('| Grade |')) {
            section = 'table';
            continue;
        }
        if (section === 'table') {
            if (line.startsWith('| ---')) {
                continue;
            }
            if (!line.startsWith('|')) {
                section = null;
                continue;
            }
            const cells = line.split('|').map((cell) => cell.trim()).filter(Boolean);
            if (cells.length >= 8) {
                rows.push({
                    grade: cells[0],
                    model: cells[1],
                    status: cells[2],
                    elapsedSeconds: parseNullableNumber(cells[3]),
                    responseChars: parseNullableNumber(cells[4]),
                    gpuUtilMax: parseNullableNumber(cells[5]),
                    gpuUtilAvg: parseNullableNumber(cells[6]),
                    gpuVramMaxMib: parseNullableNumber(cells[7]),
                });
            }
            continue;
        }
        if (section === 'preview' && line.startsWith('- ')) {
            previewLines.push(line.slice(2));
            continue;
        }
        if (section === 'issues' && line.startsWith('- ')) {
            issues.push(line.slice(2));
        }
    }

    return {
        path: reportPath,
        reportDate,
        prompt,
        maxTokens,
        rows,
        previewLines,
        issues,
    };
};

export async function fetchLatestQuantCompareSummaryBundle(options: {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    reportPrefix: string;
}) {
    const listUrl = new URL(`${options.apiBaseUrl}/api/admin/workspace-text-files`);
    listUrl.searchParams.set('path', 'reports');
    const listResponse = await options.adminFetch(listUrl.toString());
    const listPayload = await listResponse.json().catch(() => ({}));
    if (!listResponse.ok) {
        throw new Error((listPayload as any).detail || `HTTP ${listResponse.status}`);
    }

    const listing = listPayload as AdminWorkspaceTextListingLike;
    const candidates = (listing.entries || [])
        .filter((entry) => (
            entry.kind === 'file'
            && entry.name.startsWith(options.reportPrefix)
            && entry.name.endsWith('.md')
        ))
        .sort((left, right) => {
            const modifiedDiff = Number(right.modified_at || 0) - Number(left.modified_at || 0);
            if (modifiedDiff !== 0) {
                return modifiedDiff;
            }
            return right.name.localeCompare(left.name);
        });

    if (candidates.length === 0) {
        return {
            summary: null,
            message: '아직 생성된 양자화 비교 리포트가 없습니다.',
        };
    }

    const latestReport = candidates[0];
    const fileUrl = new URL(`${options.apiBaseUrl}/api/admin/workspace-text-file`);
    fileUrl.searchParams.set('path', latestReport.path);
    const fileResponse = await options.adminFetch(fileUrl.toString());
    const filePayload = await fileResponse.json().catch(() => ({}));
    if (!fileResponse.ok) {
        throw new Error((filePayload as any).detail || `HTTP ${fileResponse.status}`);
    }

    const reportFile = filePayload as AdminWorkspaceTextFileResponseLike;
    return {
        summary: parseQuantCompareReport(reportFile.path, String(reportFile.content || '')),
        message: '',
    };
}
