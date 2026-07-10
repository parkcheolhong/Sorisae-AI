/** Android는 동시에 하나의 runtime permission 다이얼로그만 허용한다. */
let permissionRequestChain: Promise<unknown> = Promise.resolve();

export function runExclusivePermissionTask<T>(task: () => Promise<T>): Promise<T> {
    const run = permissionRequestChain.then(task, task);
    permissionRequestChain = run.then(
        () => undefined,
        () => undefined,
    );
    return run;
}
