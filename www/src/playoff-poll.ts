export function waitForPlayoffRetry(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Request aborted', 'AbortError'));
      return;
    }
    const timer = setTimeout(() => {
      signal.removeEventListener('abort', abort);
      resolve();
    }, 2000);
    function abort() {
      clearTimeout(timer);
      reject(new DOMException('Request aborted', 'AbortError'));
    }
    signal.addEventListener('abort', abort, { once: true });
  });
}

export function parsePlayoffResponse<T>(
  response: unknown,
  isPicture: (value: unknown) => value is T,
): { pending: true; progress: SimulationProgress | null } | { pending: false; value: T } {
  if (typeof response === 'object' && response !== null &&
      'status' in response && response.status === 'pending') {
    const progress = 'progress' in response ? response.progress : null;
    if (progress === null) return { pending: true, progress: null };
    if (typeof progress === 'object' && progress !== null &&
        'completed' in progress && typeof progress.completed === 'number' && Number.isInteger(progress.completed) &&
        'total' in progress && typeof progress.total === 'number' && Number.isInteger(progress.total) &&
        progress.total > 0 && progress.completed >= 0 && progress.completed <= progress.total) {
      return { pending: true, progress: { completed: progress.completed, total: progress.total } };
    }
    throw new Error('The server returned invalid simulation progress.');
  }
  if (isPicture(response)) return { pending: false, value: response };
  throw new Error('The server returned an invalid playoff response.');
}

export async function pollPlayoffPicture<T>(
  load: () => Promise<{ pending: true; progress: SimulationProgress | null } | { pending: false; value: T }>,
  signal: AbortSignal,
  onPending: (progress: SimulationProgress | null) => void,
  wait = waitForPlayoffRetry,
): Promise<T> {
  while (true) {
    const result = await load();
    if (signal.aborted) throw new DOMException('Request aborted', 'AbortError');
    if (result.pending) {
      onPending(result.progress);
      await wait(signal);
    } else {
      return result.value;
    }
  }
}
export interface SimulationProgress {
  completed: number;
  total: number;
}
