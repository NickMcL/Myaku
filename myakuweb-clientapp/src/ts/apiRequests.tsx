/* Functions for making requests to MyakuWeb API */

import { recursivelyTransform } from './utils';
import {
    KanaConvertType,
    PrimativeType,
    ResourceLinksResponse,
    Search,
    SearchOptions,
    SearchResources,
    SearchResultPage,
    SearchResultPageResponse,
    SessionSearchOptionsResponse,
} from './types';

function isDatetimeKey(key: string): boolean {
    return key.endsWith('Datetime');
}

function convertIsoFormatToDate(
    isoFormatString: PrimativeType
): Date | PrimativeType {
    if (typeof isoFormatString !== 'string') {
        return isoFormatString;
    }
    return new Date(isoFormatString);
}

async function fetchJson(url: string): Promise<unknown> {
    var request = new Request(url);
    var init: RequestInit = {
        method: 'GET',
        cache: 'no-cache',
    };

    var response = await fetch(request, init);
    var responseJson = await response.json();
    recursivelyTransform(
        responseJson, convertIsoFormatToDate, isDatetimeKey
    );
    return responseJson;
}

export async function getSessionSearchOptions(): Promise<SearchOptions> {
    var requestUrl = '/api/session-search-options';
    var response = await (
        fetchJson(requestUrl) as Promise<SessionSearchOptionsResponse>
    );

    return {
        kanaConvertType: response.kanaConvertType,
    };
}

export async function getSearchResultPage(
    search: Search
): Promise<SearchResultPage> {
    var requestUrl = (
        '/api/search'
        + `?q=${search.query}`
        + `&p=${search.pageNum}`
        + `&conv=${search.options.kanaConvertType}`
    );
    var response = await (
        fetchJson(requestUrl) as Promise<SearchResultPageResponse>
    );

    return {
        search: {
            query: response.convertedQuery,
            pageNum: response.pageNum,
            options: search.options,
        },
        totalResults: response.totalResults,
        hasNextPage: response.hasNextPage,
        maxPageReached: response.maxPageReached,
        results: response.articleResults,
    };
}

export async function getSearchResources(
    query: string, kanaConvertType: KanaConvertType
): Promise<SearchResources> {
    var requestUrl = `/api/resource-links?q=${query}&conv=${kanaConvertType}`;
    var response = await (
        fetchJson(requestUrl) as Promise<ResourceLinksResponse>
    );

    return {
        query: response.convertedQuery,
        resourceLinkSets: response.resourceLinkSets,
    };
}

export async function getSearchWithResources(
    search: Search
): Promise<[SearchResultPage, SearchResources]> {
    return Promise.all([
        getSearchResultPage(search),
        getSearchResources(search.query, search.options.kanaConvertType),
    ]);
}
