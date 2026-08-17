export function beginSorisaeButtonDrag(deps: { dragMovedRef: { current: boolean }; buttonPosition: { extractOffset: () => void } }): void {
    deps.dragMovedRef.current = false;
    deps.buttonPosition.extractOffset();
}

export function markSorisaeButtonDragged(deps: { dragMovedRef: { current: boolean } }, dx: number, dy: number): void {
    if (Math.abs(dx) > 4 || Math.abs(dy) > 4) {
        deps.dragMovedRef.current = true;
    }
}

export function openSorisaeWindowIfTap(deps: { dragMovedRef: { current: boolean }; sorisaeWindowOpenRef: { current: boolean }; setSorisaeWindowOpen: (open: boolean) => void }): void {
    if (deps.dragMovedRef.current) {
        return;
    }

    deps.sorisaeWindowOpenRef.current = true;
    deps.setSorisaeWindowOpen(true);
}