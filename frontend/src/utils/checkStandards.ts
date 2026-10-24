import type { StandardInfo } from '../api';

// Keep source verification and database load bounded while avoiding a serial queue.
export const LOOKUP_CONCURRENCY = 4;

export async function checkStandardsConcurrently(
  items: StandardInfo[],
  check: (standard: StandardInfo) => Promise<void>,
  isActive: () => boolean = () => true,
): Promise<void> {
  const pending = items.filter(standard => standard.code || standard.name);
  let next = 0;
  const worker = async () => {
    // A superseded batch stops pulling new rows; in-flight rows are aborted by the caller.
    while (next < pending.length && isActive()) {
      const standard = pending[next++];
      await check(standard);
    }
  };
  await Promise.all(Array.from({ length: Math.min(LOOKUP_CONCURRENCY, pending.length) }, worker));
}
