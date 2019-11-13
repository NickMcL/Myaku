/**
 * Global types for loading webpack non-code assets into TypeScript files.
 */

/**
 * Svg image files import as the URL to that image.
 */
declare module '*.svg' {
    const sourceUrl: string;
    export default sourceUrl;
}
