/* Types used across the MyakuWeb project */

export type PrimativeType = string | number | symbol | null | undefined;

export function isPrimativeType(value: unknown): value is PrimativeType {
    return (
        value === null
        || (typeof value !== 'object'
            && typeof value !== 'function')
    );
}

export interface Indexable {
    [key: string]: unknown;
}

export function isIndexable(value: unknown): value is Indexable {
    return !isPrimativeType(value);
}

export interface SearchOptions {
    kanaConvertType: KanaConvertType;
}

export type SessionSearchOptionsResponse = SearchOptions;

export const SEARCH_OPTIONS: Array<keyof SearchOptions> = [
    'kanaConvertType',
];

export function isSearchOption(value: unknown): value is keyof SearchOptions {
    if (typeof value !== 'string') {
        return false;
    }
    return SEARCH_OPTIONS.includes(value as keyof SearchOptions);
}

export type KanaConvertType = 'hira' | 'kata' | 'none';

export const KANA_CONVERT_TYPE_VALUES: KanaConvertType[] = [
    'hira',
    'kata',
    'none',
];

export function isKanaConvertType(value: unknown): value is KanaConvertType {
    if (typeof value !== 'string') {
        return false;
    }
    return KANA_CONVERT_TYPE_VALUES.includes(value as KanaConvertType);
}

export interface ArticleSampleTextSegment {
    isQueryMatch: boolean;
    text: string;
}

export interface ArticleSampleText {
    textStartPos: string;
    segments: ArticleSampleTextSegment[];
}

export interface ArticleSearchResult {
    title: string;
    sourceName: string;
    publicationDatetime: Date;
    lastUpdatedDatetime: Date | null;
    instanceCount: number;
    tags: string[];
    mainSampleText: ArticleSampleText;
    extraSampleText: ArticleSampleText[] | null;
}

export interface SearchResultPageResponse {
    readonly convertedQuery: string;
    readonly totalResults: number;
    readonly pageNum: number;
    readonly hasNextPage: boolean;
    readonly maxPageReached: boolean;
    readonly articleResults: ArticleSearchResult[];
}

export interface ResourceLink {
    resourceName: string;
    link: string;
}

export interface ResourceLinkSet {
    setName: string;
    resourceLinks: ResourceLink[];
}

export interface ResourceLinksResponse {
    readonly convertedQuery: string;
    readonly resourceLinkSets: ResourceLinkSet[];
}
