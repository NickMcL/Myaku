/**
 * Functions for making requests to MyakuWeb API.
 * @module ts/app/apiRequests
 */

import { recursivelyTransform } from 'ts/app/utils';

import {
    KanaConvertType,
    PrimativeType,
    ResourceLinksResponse,
    Search,
    SearchResources,
    SearchResultPage,
    SearchResultPageResponse,
} from 'ts/types/types';

const REQUEST_CACHE_NAME = 'MyakuWebApiRequests';
const MAX_CACHED_REQUESTS = 100;

const DEFAULT_RESPONSE_MAX_AGE = 1800;
const CACHE_CONTROL_MAX_AGE_REGEX = /max-age=(\d+)/i;

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

function isExpired(response: Response): boolean {
    var responseDate = response.headers.get('date');
    if (responseDate === null) {
        return true;
    }

    var responseTime = (new Date(responseDate)).getTime();
    if (isNaN(responseTime)) {
        return true;
    }

    var maxAge = DEFAULT_RESPONSE_MAX_AGE;
    var cacheControlSetting = response.headers.get('cache-control');
    if (cacheControlSetting !== null) {
        const match = CACHE_CONTROL_MAX_AGE_REGEX.exec(cacheControlSetting);
        if (match !== null) {
            maxAge = Number(match[1]);
        }
    }

    return (responseTime + (maxAge * 1000)) < (new Date()).getTime();
}

async function moveToFrontOfCache(
    request: Request, response: Response
): Promise<void> {
    var cache = await window.caches.open(REQUEST_CACHE_NAME);
    await cache.delete(request);
    await cache.put(request, response);
}

async function cacheRequest(
    request: Request, response: Response
): Promise<void> {
    var cache = await window.caches.open(REQUEST_CACHE_NAME);
    var cachedRequests = await cache.keys();
    const requestsToDelete = cachedRequests.length - MAX_CACHED_REQUESTS + 1;
    if (requestsToDelete > 0) {
        for (let i = 0; i < requestsToDelete; ++i) {
            await cache.delete(cachedRequests[i]);
        }
    }

    await cache.put(request, response);
}

async function fetchJson(url: string): Promise<unknown> {
    var request = new Request(url);
    var init: RequestInit = {
        cache: 'default',
        method: 'GET',
    };

    var response = await window.caches.match(request);
    if (response && !isExpired(response)) {
        moveToFrontOfCache(request, response.clone());
    } else {
        response = await fetch(request, init);
        cacheRequest(request, response.clone());
    }

    var responseJson = await response.json();
    recursivelyTransform(
        responseJson, convertIsoFormatToDate, isDatetimeKey
    );
    return responseJson;
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
