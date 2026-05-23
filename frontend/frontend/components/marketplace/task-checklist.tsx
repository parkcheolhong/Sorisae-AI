'use client';

import React, { useEffect, useState } from 'react';

type ChecklistItem = {
    id: string;
    label: string;
    completed: boolean;
};

const initialItems: ChecklistItem[] = [
    { id: 'task-1', label: '1. 하드코딩된 API 주소 분리 (VERIFIER_API)', completed: true },
    { id: 'task-2', label: '2. 로딩/에러 상태 UI 고도화 (스켈레톤 등)', completed: true },
    { id: 'task-3', label: '3. 고객 인증 세션 처리 최적화 (향후 과제 포함)', completed: true },
    { id: 'task-4', label: '4. 모바일 반응형 점검 (레일 숨김 등)', completed: true },
    { id: 'task-5', label: '5. 좌측 레일 카테고리 분리 (모바일, 프로그램 등)', completed: true },
    { id: 'task-6', label: '6. 중앙 화면 동적 렌더링 구현', completed: true },
    { id: 'task-7', label: '7. 우측 레일 부가 기능(인증/오케스트레이터 등) 배치', completed: true },
];

interface TaskChecklistProps {
    hidden?: boolean;
}

export default function TaskChecklist(props: TaskChecklistProps) {
    const [items, setItems] = useState<ChecklistItem[]>([]);
    const [isOpen, setIsOpen] = useState(true);

    useEffect(() => {
        const saved = localStorage.getItem('marketplace-redesign-checklist');
        if (saved) {
            try {
                setItems(JSON.parse(saved));
            } catch {
                setItems(initialItems);
            }
        } else {
            setItems(initialItems);
        }
    }, []);

    const toggleItem = (id: string) => {
        const newItems = items.map(item =>
            item.id === id ? { ...item, completed: !item.completed } : item
        );
        setItems(newItems);
        localStorage.setItem('marketplace-redesign-checklist', JSON.stringify(newItems));
    };

    if (items.length === 0) return null;

    const completedCount = items.filter(i => i.completed).length;
    const progress = Math.round((completedCount / items.length) * 100);

    if (props.hidden) {
        return null;
    }

    return (
        <div className="fixed bottom-6 right-6 z-40 hidden w-80 overflow-hidden rounded-2xl border border-[#30363d] bg-[#0d1117] shadow-xl transition-all duration-300 lg:block">
            <div 
                className="flex cursor-pointer items-center justify-between border-b border-[#30363d] bg-[#161b22] px-4 py-3"
                onClick={() => setIsOpen(!isOpen)}
            >
                <div>
                    <h3 className="text-sm font-bold text-white">UI/UX 설계 체크리스트</h3>
                    <div className="mt-1 flex items-center gap-2">
                        <div className="h-1.5 w-32 overflow-hidden rounded-full bg-[#30363d]">
                            <div className="h-full bg-[#2a7cff] transition-all duration-500" style={{ width: `${progress}%` }} />
                        </div>
                        <span className="text-xs text-[#98a3b3]">{progress}%</span>
                    </div>
                </div>
                <button className="text-[#98a3b3] hover:text-white">
                    {isOpen ? '▼' : '▲'}
                </button>
            </div>
            
            {isOpen && (
                <div className="max-h-96 overflow-y-auto p-2">
                    {items.map((item) => (
                        <label 
                            key={item.id} 
                            className={`flex cursor-pointer items-start gap-3 rounded-lg p-2 transition-colors hover:bg-[#161b22] ${item.completed ? 'opacity-50' : ''}`}
                        >
                            <input 
                                type="checkbox" 
                                checked={item.completed}
                                onChange={() => toggleItem(item.id)}
                                className="mt-1 h-4 w-4 rounded border-[#30363d] bg-transparent accent-[#2a7cff]"
                            />
                            <span className={`text-sm leading-tight ${item.completed ? 'text-[#98a3b3] line-through' : 'text-[#d2d9e3]'}`}>
                                {item.label}
                            </span>
                        </label>
                    ))}
                </div>
            )}
        </div>
    );
}
