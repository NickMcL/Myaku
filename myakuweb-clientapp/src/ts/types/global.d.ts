/** Global types for loading webpack non-code assets into TypeScript files */

declare module '*.svg' {
    const sourceUrl: string;
    export default sourceUrl;
}
