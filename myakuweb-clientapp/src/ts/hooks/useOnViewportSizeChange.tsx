/**
 * @module ts/hooks/useOnViewportSizeChange
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
