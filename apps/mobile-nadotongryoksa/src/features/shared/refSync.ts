export function syncRefCurrent<T>(ref: { current: T }, value: T): void {
    ref.current = value;
}