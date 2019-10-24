/**
 * Constants and functions for browser viewport breakpoints.
 * @module viewport
 */

export const enum ViewportSize {
    XSmall = 0,
    Small = 576,
    Medium = 768,
    Large = 992,
    XLarge = 1200,
}

export function getViewportSize(): ViewportSize {
    if (window.innerWidth >= ViewportSize.XLarge) {
        return ViewportSize.XLarge;
    } else if (window.innerWidth >= ViewportSize.Large) {
        return ViewportSize.Large;
    } else if (window.innerWidth >= ViewportSize.Medium) {
        return ViewportSize.Medium;
    } else if (window.innerWidth >= ViewportSize.Small) {
        return ViewportSize.Small;
    } else {
        return ViewportSize.XSmall;
    }
}
