/**
 * useInputClearHandler hook module. See [[useInputClearHandler]].
 */

import { useCallback } from 'react';

/**
 * Hook for a handler that clears the current value of an input.
 *
 * @param onChange - Handler to call with the new value of an input whenever it
 * changes.
 */
export default function useInputClearHandler<T extends string>(
    onChange: (newValue: T) => void
): () => void {
    return useCallback((): void => onChange('' as T), [onChange]);
}
