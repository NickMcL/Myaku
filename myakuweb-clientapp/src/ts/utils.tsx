/** @module Utility functions for the MyakuWeb project */

import {
    Indexable,
    PrimativeType,
    isIndexable,
    isPrimativeType,
} from './types';

export function recursivelyApply(
    obj: Indexable,
    applyFunc: (value: PrimativeType) => unknown,
    condFunc?: (key: string, value: PrimativeType) => boolean
): void {
    for (const [key, value] of Object.entries(obj)) {
        if (isIndexable(value) && typeof value !== 'function') {
            recursivelyApply(value, applyFunc, condFunc);
        } else if (
            isPrimativeType(value) && condFunc && condFunc(key, value)
        ) {
            obj[key] = applyFunc(value);
        }
    }
}

/**
 * Forces a redraw of the element by the browser.
 */
export function reflow(element: HTMLElement): number {
    return element.offsetHeight;
}
