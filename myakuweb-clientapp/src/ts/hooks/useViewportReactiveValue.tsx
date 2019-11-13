/**
 * useViewportReactiveValue hook module. See [[useViewportReactiveValue]].
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


/**
 * Based on the given viewport size value map, get which value should be used
 * for the given viewport size.
 *
 * @typeparam T - The type of value to be returned.
 *
 * @param viewportSize - Viewport size to get the value for
 * @param defaultValue - The value to return by default if none of the values
 * in viewportSizeValues are applicable to the given viewport size.
 * @param viewportSizeValues - A map from viewport sizes to values.
 *
 * @returns
 * If a viewport size less than or equal to the given viewport size is in
 * viewportSizeValues, returns the value for the largest viewport size less
 * than or equal to the given viewport size.
 *
 * If no viewport size less than or equal to the given viewport size is in
 * viewportSizeValues, returns defaultValue.
 */
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

/**
 * Hook for a value that changes based on the current viewport size.
 *
 * @typeparam T - The type of value to be returned by the hook.
 *
 * @param defaultValue - The value that will be returned by the hook by default
 * if none of the values in viewportSizeValues are applicable to the current
 * viewport size.
 * @param viewportSizeValues - A map from viewport sizes to values.
 *
 * @returns
 * Based on the current viewport size.
 *
 * If a viewport size less than or equal to the current viewport size is in
 * viewportSizeValues, returns the value for the largest viewport size less
 * than or equal to the current viewport size.
 *
 * If no viewport size less than or equal to the current viewport size is in
 * viewportSizeValues, returns defaultValue.
 */
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
