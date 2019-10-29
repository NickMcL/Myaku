/**
 * Functions for making requests to MyakuWeb API.
 * @module ts/app/apiRequests
 */

import { recursivelyTransform } from 'ts/app/utils';

import {
    Indexable,
    KanaConvertType,
    PrimativeType,
    ResourceLinksResponse,
    Search,
    SearchResources,
    SearchResultPage,
    SearchResultPageResponse,
} from 'ts/types/types';

interface CachedResponse {
    expireTime: number;
    json: Indexable;
}

const CACHED_REQUEST_ORDER_KEY = 'CachedRequestOrder';
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

function isExpired(cachedResponse: CachedResponse): boolean {
    return cachedResponse.expireTime <= (new Date()).getTime();
}

function getExpireTime(response: Response): number {
    var responseDate = response.headers.get('date');
    if (responseDate === null) {
        return 0;
    }

    var responseTime = (new Date(responseDate)).getTime();
    if (isNaN(responseTime)) {
        return 0;
    }

    var maxAge = DEFAULT_RESPONSE_MAX_AGE;
    var cacheControlSetting = response.headers.get('cache-control');
    if (cacheControlSetting !== null) {
        const match = CACHE_CONTROL_MAX_AGE_REGEX.exec(cacheControlSetting);
        if (match !== null) {
            maxAge = Number(match[1]);
        }
    }

    return (responseTime + (maxAge * 1000)) + 1;
}

function freeCacheSpace(): boolean {
    var cachedRequestOrderStr = window.sessionStorage.getItem(
        CACHED_REQUEST_ORDER_KEY
    );
    if (cachedRequestOrderStr === null) {
        return false;
    }

    var cachedRequestOrder = JSON.parse(cachedRequestOrderStr) as string[];
    var itemsToDelete = Math.ceil(cachedRequestOrder.length / 2);
    for (let i = 0; i < itemsToDelete; ++i) {
        window.sessionStorage.removeItem(cachedRequestOrder[i]);
    }
    window.sessionStorage.setItem(
        CACHED_REQUEST_ORDER_KEY,
        JSON.stringify(cachedRequestOrder.splice(0, itemsToDelete))
    );

    return (cachedRequestOrder.length - itemsToDelete) > 0;
}

function isOutOfSpaceException(exception: DOMException): boolean {
    if (exception.code === 22 || exception.code === 1014) {
        return true;
    }
    return false;
}

function freeSpaceAndCache(key: string, value: string): void {
    var canFreeMore = true;
    while (canFreeMore) {
        try {
            window.sessionStorage.setItem(key, value);
            break;
        } catch (e) {
            if (isOutOfSpaceException(e)) {
                canFreeMore = freeCacheSpace();
            } else {
                throw e;
            }
        }
    }
}

function addToCachedRequestOrder(requestUrl: string): void {
    var cachedRequestOrder: string[];
    var cachedRequestOrderStr = window.sessionStorage.getItem(
        CACHED_REQUEST_ORDER_KEY
    );
    if (cachedRequestOrderStr === null) {
        cachedRequestOrder = [requestUrl];
    } else {
        cachedRequestOrder = JSON.parse(cachedRequestOrderStr) as string[];
        cachedRequestOrder.push(requestUrl);
    }

    freeSpaceAndCache(
        CACHED_REQUEST_ORDER_KEY, JSON.stringify(cachedRequestOrder)
    );
}

async function cacheRequest(
    requestUrl: string, response: Response
): Promise<Indexable> {
    const cachedResponse: CachedResponse = {
        expireTime: getExpireTime(response),
        json: await response.json(),
    };
    addToCachedRequestOrder(requestUrl);
    freeSpaceAndCache(requestUrl, JSON.stringify(cachedResponse));

    return cachedResponse.json;
}

async function fetchJson(url: string): Promise<unknown> {
    var request = new Request(url);
    var init: RequestInit = {
        cache: 'default',
        method: 'GET',
    };

    var responseJson = null;
    const cachedResponseStr = window.sessionStorage.getItem(url);
    if (cachedResponseStr !== null) {
        const cachedResponse = JSON.parse(cachedResponseStr) as CachedResponse;
        if (!isExpired(cachedResponse)) {
            responseJson = cachedResponse.json;
        }
    }

    if (responseJson === null) {
        const response = await fetch(request, init);
        responseJson = await cacheRequest(url, response);
    }

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
