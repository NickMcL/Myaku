/**
 * useInputChangeHandler hook module. See [[useInputChangeHandler]].
 */

import { useCallback } from 'react';


/**
 * Hook for a handler that calls a callback with the current value of an input
 * on changes.
 *
 * @param onChange - Handler to call with the new value of an input whenever it
 * changes.
 */
export default function useInputChangeHandler<T extends string>(
    onChange: (newValue: T) => void
): (event: React.FormEvent<HTMLInputElement>) => void {
    return useCallback(
        function(event: React.FormEvent<HTMLInputElement>): void {
            onChange(event.currentTarget.value as T);
        },
        [onChange]
    );
}
