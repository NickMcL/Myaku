/**
 * Hook for a value that changes based on the current viewport size.
 *
 * @module ts/hooks/useViewportReactiveValue
 */

import useOnViewpotSizeChange from 'ts/hooks/useOnViewportSizeChange';

import {
    ViewportSize,
    getViewportSize,
} from 'ts/app/viewport';
import {
    useCallback,
    useEffect,
    useState,
} from 'react';


function getValueForViewport<T>(
    viewportSize: ViewportSize, defaultValue: T,
    viewportSizeValues: Partial<Record<ViewportSize, T>>
): T {
    var xlargeValue = viewportSizeValues[ViewportSize.XLarge];
    if (viewportSize >= ViewportSize.XLarge && xlargeValue !== undefined) {
        return xlargeValue;
    }

    var largeValue = viewportSizeValues[ViewportSize.Large];
    if (viewportSize >= ViewportSize.Large && largeValue !== undefined) {
        return largeValue;
    }

    var mediumValue = viewportSizeValues[ViewportSize.Medium];
    if (viewportSize >= ViewportSize.Medium && mediumValue !== undefined) {
        return mediumValue;
    }

    var smallValue = viewportSizeValues[ViewportSize.Small];
    if (viewportSize >= ViewportSize.Small && smallValue !== undefined) {
        return smallValue;
    }

    var xsmallValue = viewportSizeValues[ViewportSize.XSmall];
    if (viewportSize >= ViewportSize.XSmall && xsmallValue !== undefined) {
        return xsmallValue;
    }

    return defaultValue;
}

export default function useViewportReactiveValue<T>(
    defaultValue: T,
    viewportSizeValues: Partial<Record<ViewportSize, T>>
): T {
    const [value, setValue] = useState(defaultValue);
    const handleViewportSizeChange = useCallback(
        function(newViewportSize: ViewportSize): void {
            const newValue = getValueForViewport<T>(
                newViewportSize, defaultValue, viewportSizeValues
            );
            setValue(newValue);
        },
        [defaultValue, viewportSizeValues]
    );
    useOnViewpotSizeChange(handleViewportSizeChange);

    // useOnViewportSizeChange handles updating the value in response to
    // viewport size changes, but the value still needs to be updated based on
    // the initial viewport size when the component using the value is first
    // rendered.
    useEffect((): void => handleViewportSizeChange(getViewportSize()));

    return value;
}
