import { useState } from 'react';

export interface AdminWorkspaceTextEntry {
    name: string;
    path: string;
    kind: 'dir' | 'file';
    size_bytes?: number | null;
    modified_at?: number | null;
}

export interface AdminWorkspaceTextListing {
    root_path: string;
    current_path: string;
    parent_path?: string | null;
    entries: AdminWorkspaceTextEntry[];
}

interface UseAdminWorkspaceOptions {
    apiBaseUrl: string;
    adminFetch: (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;
    getEffectiveTaskInput: () => string;
    setUnifiedPrompt: (value: string) => void;
}

export function useAdminWorkspace(options: UseAdminWorkspaceOptions) {
    const [workspaceListing, setWorkspaceListing] = useState<AdminWorkspaceTextListing | null>(null);
    const [workspaceBrowsePath, setWorkspaceBrowsePath] = useState('');
    const [workspaceLoading, setWorkspaceLoading] = useState(false);
    const [workspaceMessage, setWorkspaceMessage] = useState('');
    const [importMode, setImportMode] = useState<'append' | 'replace'>('append');

    const injectImportedText = (sourcePath: string, content: string) => {
        const normalizedBlock = `[불러온 파일]\n경로: ${sourcePath}\n\n${content}`;
        const baseText = importMode === 'replace' ? '' : options.getEffectiveTaskInput();
        const nextText = baseText
            ? `${baseText}\n\n${normalizedBlock}`
            : normalizedBlock;
        options.setUnifiedPrompt(nextText);
        setWorkspaceMessage(
            `통합 입력창에 ${sourcePath} 전체 본문을 ${importMode === 'replace' ? '교체' : '추가'}했습니다.`,
        );
    };

    const importWorkspaceFile = async (path: string) => {
        setWorkspaceLoading(true);
        setWorkspaceMessage('');
        try {
            const url = new URL(`${options.apiBaseUrl}/api/admin/workspace-text-file`);
            url.searchParams.set('path', path);
            const response = await options.adminFetch(url.toString());
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error((data as any).detail || `HTTP ${response.status}`);
            }
            injectImportedText(String((data as any).path || path), String((data as any).content || ''));
        } catch (e: any) {
            setWorkspaceMessage(`파일 불러오기 실패: ${e.message}`);
        } finally {
            setWorkspaceLoading(false);
        }
    };

    const fetchWorkspaceListing = async (requestedPath?: string) => {
        setWorkspaceLoading(true);
        setWorkspaceMessage('');
        try {
            const url = new URL(`${options.apiBaseUrl}/api/admin/workspace-text-files`);
            if (requestedPath?.trim()) {
                url.searchParams.set('path', requestedPath.trim());
            }
            const response = await options.adminFetch(url.toString());
            const data = await response.json().catch(() => ({}));
            if (!response.ok) {
                throw new Error((data as any).detail || `HTTP ${response.status}`);
            }
            const listing = data as AdminWorkspaceTextListing;
            setWorkspaceListing(listing);
            setWorkspaceBrowsePath(listing.current_path || requestedPath || '');
            return listing;
        } catch (e: any) {
            setWorkspaceMessage(`작업 폴더 조회 실패: ${e.message}`);
            return null;
        } finally {
            setWorkspaceLoading(false);
        }
    };

    const resolveWorkspacePath = (...fallbackCandidates: Array<string | null | undefined>) => {
        return String(
            workspaceListing?.current_path
            || workspaceListing?.root_path
            || workspaceBrowsePath
            || fallbackCandidates.find((candidate) => String(candidate || '').trim())
            || '',
        ).trim();
    };

    const syncWorkspacePath = async (path?: string) => {
        const normalizedPath = String(path || '').trim();
        if (!normalizedPath) {
            return fetchWorkspaceListing();
        }
        setWorkspaceBrowsePath(normalizedPath);
        return fetchWorkspaceListing(normalizedPath);
    };

    return {
        workspaceListing,
        workspaceBrowsePath,
        workspaceLoading,
        workspaceMessage,
        importMode,
        setWorkspaceListing,
        setWorkspaceBrowsePath,
        setWorkspaceMessage,
        setImportMode,
        injectImportedText,
        importWorkspaceFile,
        fetchWorkspaceListing,
        resolveWorkspacePath,
        syncWorkspacePath,
    };
}
