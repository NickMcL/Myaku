/**
 * Hook for a handler that clears the current value of an input.
 * @module ts/hooks/useInputClearHandler
 */

import { useCallback } from 'react';


export default function useInputClearHandler<T extends string>(
    onChange: (newValue: T) => void
): () => void {
    return useCallback((): void => onChange('' as T), [onChange]);
}
