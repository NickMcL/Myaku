/**
 * Constants and functions for browser viewport breakpoints.
 */

/**
 * Each viewport size constant has its value set as the minimum size in pixels
 * of that viewport size.
 *
 * This allows one to do comparisons like Large \> Small to compare viewport
 * sizes.
 */
export const enum ViewportSize {
    XSmall = 0,
    Small = 576,
    Medium = 768,
    Large = 992,
    XLarge = 1200,
}

/**
 * Get the current viewport size of the window.
 */
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
