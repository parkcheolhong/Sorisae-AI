import type { AdminGeneratorDetailModalData } from '@/components/admin/admin-generator-detail-modal';

export function buildAdminGeneratorModalBindings(options: {
    modal: AdminGeneratorDetailModalData | null;
    onClose: () => void;
    onSelectAction: (actionId: string) => void;
}) {
    return {
        modal: options.modal,
        onClose: options.onClose,
        onSelectAction: options.onSelectAction,
    };
}
