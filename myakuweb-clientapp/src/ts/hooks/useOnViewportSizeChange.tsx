/**
 * useOnViewportSizeChange hook module. See [[useOnViewportSizeChange]].
 */

import {
    ViewportSize,
    getViewportSize,
} from 'ts/app/viewport';
import {
    useCallback,
    useEffect,
} from 'react';

interface ViewportSizeChangeCallback {
    (viewportSize: ViewportSize): void;
}


/**
 * Get a handler that will call the given callback when called if the viewport
 * size has changed from one [[ViewportSize]] to another since the last time
 * the handler was called.
 *
 * @param callback - Callback to call on viewport size changes.
 */
function getViewportSizeChangeHandler(
    callback: ViewportSizeChangeCallback
): () => void {
    var previousViewportSize: number | null = null;
    return function(): void {
        if (previousViewportSize === null) {
            previousViewportSize = getViewportSize();
        }

        var currentViewportSize = getViewportSize();
        if (currentViewportSize !== previousViewportSize) {
            previousViewportSize = currentViewportSize;
            callback(currentViewportSize);
        }
    };
}

/**
 * Hook that calls a callback whenever the viewport size changes.
 *
 * The callback will only be called when the viewport size changes from one of
 * the sizes in [[ViewportSize]] to another.
 *
 * This means the callback is NOT called necessarily every time the window size
 * changes because it is not called if a change was small enough that it didn't
 * cause a change from one [[ViewportSize]] to another.
 */
export default function useOnViewpotSizeChange(
    callback: ViewportSizeChangeCallback
): void {
    const memoizedCallback = useCallback(
        getViewportSizeChangeHandler(callback), [callback]
    );

    useEffect(function(): () => void {
        window.addEventListener('resize', memoizedCallback);
        return function(): void {
            window.removeEventListener('resize', memoizedCallback);
        };
    }, [memoizedCallback]);
}
