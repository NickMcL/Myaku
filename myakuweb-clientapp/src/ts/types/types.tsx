/**
 * Types used across the MyakuWeb app.
 */

/** Makes the type of every key of an object nullable. */
export type AllNullable<T> = {
    [P in keyof T]: T[P] | null;
};

/** The built-in non-object types in javascript. */
export type PrimativeType = (
    string | boolean | number | symbol | null | undefined
);

/**
 * Type guard function for checking that a value is a [[PrimativeType]].
 */
export function isPrimativeType(value: unknown): value is PrimativeType {
    return (
        value === null
        || (typeof value !== 'object'
            && typeof value !== 'function')
    );
}

/** Type that supports indexing to get some value (e.g. objects). */
export interface Indexable {
    [key: string]: unknown;
}

/**
 * Type guard function for checking that a value is a [[Indexable]].
 */
export function isIndexable(value: unknown): value is Indexable {
    return !isPrimativeType(value);
}

/** Possible conversion types between romaji and kana. */
export type KanaConvertType = 'hira' | 'kata' | 'none';

/** Array containing all of the valid [[KanaConvertType]] values. */
export const KANA_CONVERT_TYPE_VALUES: KanaConvertType[] = [
    'hira',
    'kata',
    'none',
];

/**
 * Type guard function for checking that a value is a [[KanaConvertType]].
 */
export function isKanaConvertType(value: unknown): value is KanaConvertType {
    if (typeof value !== 'string') {
        return false;
    }
    return KANA_CONVERT_TYPE_VALUES.includes(value as KanaConvertType);
}

/**
 * Search options that can be optionally specified along with a [[Search]].
 */
export interface SearchOptions {
    kanaConvertType: KanaConvertType;
}

/** Array containing all of the valid [[SearchOptions]] keys. */
export const SEARCH_OPTIONS: Array<keyof SearchOptions> = [
    'kanaConvertType',
];

/**
 * Type guard function for checking that a value is a [[SearchOptions]] key.
 */
export function isSearchOption(value: unknown): value is keyof SearchOptions {
    if (typeof value !== 'string') {
        return false;
    }
    return SEARCH_OPTIONS.includes(value as keyof SearchOptions);
}

/**
 * Type assert function for asserting that a value is a [[SearchOptions]] key.
 */
export function assertIsSearchOption(
    value: unknown
): asserts value is keyof SearchOptions {
    if (!isSearchOption(value)) {
        throw new Error(`"${value}" is not a valid search option`);
    }
}

/** The required parameters to make a MyakuWeb search */
export interface Search {
    query: string;
    pageNum: number;
}

/** A single segment of text from an [[ArticleSampleText]]. */
export interface ArticleSampleTextSegment {
    isQueryMatch: boolean;
    text: string;
}

/** Sample text for an article for an [[ArticleSearchResult]]. */
export interface ArticleSampleText {
    textStartPos: string;
    segments: ArticleSampleTextSegment[];
}

/** A single search result for a MyakuWeb search. */
export interface ArticleSearchResult {
    articleId: string;
    title: string;
    sourceName: string;
    sourceUrl: string;
    publicationDatetime: Date;
    lastUpdatedDatetime: Date | null;
    instanceCount: number;
    tags: string[];
    mainSampleText: ArticleSampleText;
    moreSampleTexts: ArticleSampleText[];
}

/** A page of search results for a MyakuWeb search. */
export interface SearchResultPage {
    search: Search;
    totalResults: number;
    hasNextPage: boolean;
    maxPageReached: boolean;
    results: ArticleSearchResult[];
}

/**
 * The search results page response JSON format for the MyakuWeb search API.
 */
export interface SearchResultPageResponse {
    readonly totalResults: number;
    readonly pageNum: number;
    readonly hasNextPage: boolean;
    readonly maxPageReached: boolean;
    readonly articleResults: ArticleSearchResult[];
}

/** A single resource link from a [[ResourceLinkSet]]. */
export interface ResourceLink {
    resourceName: string;
    link: string;
}

/** A set of resource links to accompany a MyakuWeb search. */
export interface ResourceLinkSet {
    setName: string;
    resourceLinks: ResourceLink[];
}

/** Resources to accompany a MyakuWeb search. */
export interface SearchResources {
    query: string;
    resourceLinkSets: ResourceLinkSet[];
}

/** The search resources response JSON format for the MyakuWeb search API. */
export interface ResourceLinksResponse {
    readonly resourceLinkSets: ResourceLinkSet[];
}
