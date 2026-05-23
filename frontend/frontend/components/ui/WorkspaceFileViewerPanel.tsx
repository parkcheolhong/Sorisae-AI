'use client';

import * as React from 'react';

export type WorkspaceFileViewerEntry = {
    path: string;
    name: string;
    kind: 'dir' | 'file';
};

export type WorkspaceFileViewerListing = {
    current_path?: string;
    parent_path?: string | null;
    entries?: WorkspaceFileViewerEntry[];
};

interface WorkspaceFileViewerPanelProps {
    workspaceBrowsePath: string;
    onSetWorkspaceBrowsePath: (value: string) => void;
    workOutputDir: string;
    liveOutputDir: string;
    onRefreshWorkspaceListing: (path?: string) => Promise<void>;
    workspaceListing: WorkspaceFileViewerListing | null;
    workspaceMessage: string;
    workspaceLoading: boolean;
    selectedWorkspaceFilePath: string;
    selectedWorkspaceFileSize: number | null;
    workspaceFileLoading: boolean;
    selectedWorkspaceFileContent: string;
    onPreviewWorkspaceFile: (path: string) => Promise<void>;
    onImportWorkspaceFile: (path: string) => Promise<void>;
}

export default function WorkspaceFileViewerPanel({
    workspaceBrowsePath,
    onSetWorkspaceBrowsePath,
    workOutputDir,
    liveOutputDir,
    onRefreshWorkspaceListing,
    workspaceListing,
    workspaceMessage,
    workspaceLoading,
    selectedWorkspaceFilePath,
    selectedWorkspaceFileSize,
    workspaceFileLoading,
    selectedWorkspaceFileContent,
    onPreviewWorkspaceFile,
    onImportWorkspaceFile,
}: WorkspaceFileViewerPanelProps) {
    return (
        <div className="mb-4 rounded-lg border border-[#30363d] bg-[#11161d] p-4 text-sm text-[#e6edf3]">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                    <p className="text-sm font-semibold text-white">작업 폴더 / 파일 코드 뷰어</p>
                    <p className="mt-1 text-xs text-[#8b949e]">현재 작업 폴더의 파일 목록과 선택 파일 코드를 같은 화면에서 확인합니다.</p>
                </div>
                <div className="flex flex-wrap gap-2 text-xs">
                    <button
                        type="button"
                        onClick={() => void onRefreshWorkspaceListing(workspaceBrowsePath || workOutputDir || liveOutputDir || undefined)}
                        className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-[#e6edf3]"
                    >
                        새로고침
                    </button>
                    {workspaceListing?.parent_path && (
                        <button
                            type="button"
                            onClick={() => void onRefreshWorkspaceListing(workspaceListing.parent_path || undefined)}
                            className="rounded-lg border border-[#30363d] bg-[#161b22] px-3 py-2 text-[#e6edf3]"
                        >
                            상위 폴더
                        </button>
                    )}
                </div>
            </div>
            <div className="mt-3 grid grid-cols-1 gap-4 xl:grid-cols-[360px_minmax(0,1fr)]">
                <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-3">
                    <label className="mb-2 block text-xs font-semibold text-[#79c0ff]">현재 작업 폴더</label>
                    <div className="flex gap-2">
                        <input
                            value={workspaceBrowsePath}
                            onChange={(e) => onSetWorkspaceBrowsePath(e.target.value)}
                            className="flex-1 rounded-lg border border-[#30363d] bg-[#11161d] px-3 py-2 text-xs text-[#e6edf3]"
                        />
                        <button
                            type="button"
                            onClick={() => void onRefreshWorkspaceListing(workspaceBrowsePath || undefined)}
                            className="rounded-lg bg-[#1f6feb] px-3 py-2 text-xs font-semibold text-white"
                        >
                            열기
                        </button>
                    </div>
                    {workspaceMessage && <p className="mt-2 text-xs text-[#f78166]">{workspaceMessage}</p>}
                    <div className="mt-3 max-h-[420px] space-y-2 overflow-y-auto pr-1 text-xs">
                        {workspaceLoading && <p className="text-[#8b949e]">폴더를 불러오는 중입니다.</p>}
                        {!workspaceLoading && (workspaceListing?.entries || []).length === 0 && (
                            <p className="text-[#8b949e]">표시할 파일 또는 폴더가 없습니다.</p>
                        )}
                        {(workspaceListing?.entries || []).map((entry) => (
                            <div key={entry.path} className="flex items-center gap-2 rounded-lg border border-[#30363d] bg-[#11161d] px-3 py-2">
                                <button
                                    type="button"
                                    onClick={() => entry.kind === 'dir' ? void onRefreshWorkspaceListing(entry.path) : void onPreviewWorkspaceFile(entry.path)}
                                    className={`flex-1 text-left ${entry.path === selectedWorkspaceFilePath ? 'text-[#79c0ff]' : 'text-[#e6edf3]'}`}
                                >
                                    <span className="mr-2">{entry.kind === 'dir' ? '📁' : '📄'}</span>
                                    {entry.name}
                                </button>
                                {entry.kind === 'file' && (
                                    <button
                                        type="button"
                                        onClick={() => void onImportWorkspaceFile(entry.path)}
                                        className="rounded-md border border-[#30363d] bg-[#161b22] px-2 py-1 text-[11px] text-[#c9d1d9]"
                                    >
                                        입력창 반영
                                    </button>
                                )}
                            </div>
                        ))}
                    </div>
                </div>
                <div className="rounded-lg border border-[#30363d] bg-[#0d1117] p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                            <p className="text-xs font-semibold text-[#79c0ff]">파일 코드 미리보기</p>
                            <p className="mt-1 text-[11px] text-[#8b949e]">{selectedWorkspaceFilePath || '파일을 선택하면 코드가 표시됩니다.'}</p>
                        </div>
                        {selectedWorkspaceFilePath && (
                            <span className="text-[11px] text-[#8b949e]">{selectedWorkspaceFileSize != null ? `${selectedWorkspaceFileSize.toLocaleString('ko-KR')} bytes` : '-'}</span>
                        )}
                    </div>
                    <div className="mt-3 max-h-[520px] overflow-auto rounded-lg border border-[#30363d] bg-[#11161d] p-3">
                        {workspaceFileLoading ? (
                            <p className="text-xs text-[#8b949e]">파일 코드를 불러오는 중입니다.</p>
                        ) : selectedWorkspaceFilePath ? (
                            <pre className="whitespace-pre-wrap break-words text-xs text-[#c9d1d9]">{selectedWorkspaceFileContent}</pre>
                        ) : (
                            <p className="text-xs text-[#8b949e]">왼쪽 파일 목록에서 코드를 확인할 파일을 선택해 주세요.</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
