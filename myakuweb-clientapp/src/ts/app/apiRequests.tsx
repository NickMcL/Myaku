/**
 * Functions for making search requests to the MyakuWeb API.
 */

import { recursivelyTransform } from 'ts/app/utils';

import {
    PrimativeType,
    ResourceLinksResponse,
    Search,
    SearchResources,
    SearchResultPage,
    SearchResultPageResponse,
} from 'ts/types/types';

interface ApiResponse {
    expireTime: number;
    json: unknown;
}

const API_RESPONSE_ERROR_KEY = 'errors';

const CACHED_REQUEST_ORDER_KEY = 'CachedRequestOrder';
const DEFAULT_RESPONSE_MAX_AGE = 3600;  // in seconds
const CACHE_CONTROL_MAX_AGE_REGEX = /max-age=(\d+)/i;


/**
 * Return true if the given key from a MyakuWeb API response is from a datetime
 * ISO string value.
 */
function isDatetimeKey(key: string): boolean {
    return key.endsWith('Datetime');
}

/**
 * Converts an ISO format datetime string to a javascript Date object.
 *
 * If the given value does not have a type of string, returns the given value
 * with no modifications.
 */
function convertIsoFormatToDate(
    isoFormatString: PrimativeType
): Date | PrimativeType {
    if (typeof isoFormatString !== 'string') {
        return isoFormatString;
    }
    return new Date(isoFormatString);
}

/**
 * Return true if the given ApiResponse is expired based on the current time.
 */
function isExpired(apiResponse: ApiResponse): boolean {
    return apiResponse.expireTime <= (new Date()).getTime();
}

/**
 * Get the cache expire time for a given MyakuWeb API response.
 *
 * Uses the 'date' and 'cache-control' headers from the response to determine
 * the expire time.
 *
 * If the response does not have valid 'date' header, returns 0 to indicate
 * that the response is already expired and shouldn't be cached.
 *
 * If the response has a valid 'date' header, but does not have a valid
 * 'cache-control' header, returns [[DEFAULT_RESPONSE_MAX_AGE]].
 *
 * @param response - A MyakuWeb API response.
 *
 * @returns The cache expire time for the given response as an epoch time.
 */
function getExpireTime(response: Response): number {
    const responseDate = response.headers.get('date');
    if (responseDate === null) {
        return 0;
    }

    const responseTime = (new Date(responseDate)).getTime();
    if (isNaN(responseTime)) {
        return 0;
    }

    var maxAge = DEFAULT_RESPONSE_MAX_AGE;
    const cacheControlSetting = response.headers.get('cache-control');
    if (cacheControlSetting !== null) {
        const match = CACHE_CONTROL_MAX_AGE_REGEX.exec(cacheControlSetting);
        if (match !== null) {
            maxAge = Number(match[1]);
        }
    }

    // maxAge is in seconds while responseTime is in milliseconds, so must
    // multiply maxAge by 1000 to convert it to milliseconds.
    // A response expires the second after responseTime + maxAge, so 1 must be
    // added to get the expire time.
    return (responseTime + (maxAge * 1000)) + 1;
}

/**
 * Attempt to free space in session storage by clearing out previously cached
 * API responses.
 *
 * Attempts to delete half of the API responses currently stored in session
 * storage going from the oldest response to newest.
 *
 * @returns True if cache space was successfully freed in session storage, and
 * false if no cache space could be freed in session storage.
 */
function freeCacheSpace(): boolean {
    const cachedRequestOrderStr = window.sessionStorage.getItem(
        CACHED_REQUEST_ORDER_KEY
    );
    if (cachedRequestOrderStr === null) {
        return false;
    }

    var cachedRequestOrder = JSON.parse(cachedRequestOrderStr) as string[];
    if (cachedRequestOrder.length === 0) {
        return false;
    }

    const itemsToDelete = Math.ceil(cachedRequestOrder.length / 2);
    for (let i = 0; i < itemsToDelete; ++i) {
        window.sessionStorage.removeItem(cachedRequestOrder[i]);
    }
    window.sessionStorage.setItem(
        CACHED_REQUEST_ORDER_KEY,
        JSON.stringify(cachedRequestOrder.splice(0, itemsToDelete))
    );
    return true;
}

/**
 * Return true if the given DOMException is an exception from the browser
 * indicating that session storage is out of space.
 */
function isOutOfSpaceException(exception: DOMException): boolean {
    // Firefox uses code 1014, but all other major browsers use code 22.
    if (exception.code === 22 || exception.code === 1014) {
        return true;
    }
    return false;
}

/**
 * Attempt to cache the given key-value pair in session storage, freeing space
 * by deleting previous API responses cached in session storage as necessary.
 *
 * This function is BEST EFFORT. Even after freeing as much space in session
 * storage as possible, if there still is not enough space to cache the given
 * key-value pair (possibly because the browser won't let anything be stored in
 * session storage), the function gives up and does not cache it.
 */
function freeSpaceAndCache(key: string, value: string): void {
    var cacheSpaceFreed = true;
    while (cacheSpaceFreed) {
        try {
            window.sessionStorage.setItem(key, value);
            break;
        } catch (e) {
            if (isOutOfSpaceException(e)) {
                cacheSpaceFreed = freeCacheSpace();
            } else {
                throw e;
            }
        }
    }
}

/**
 * Add the given URL to the end of the list in session storage of API request
 * URLs that have a cached response.
 *
 * This function is BEST EFFORT. See the warning in the comment of
 * [[freeSpaceAndCache]] for more info.
 */
function addToCachedRequestOrder(requestUrl: string): void {
    var cachedRequestOrder: string[];
    const cachedRequestOrderStr = window.sessionStorage.getItem(
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

/**
 * Cache the given response for the given request URL in session storage.
 *
 * This function is BEST EFFORT. See the warning in the comment of
 * [[freeSpaceAndCache]] for more info.
 */
function cacheApiResponse(
    requestUrl: string, apiResponse: ApiResponse
): void {
    addToCachedRequestOrder(requestUrl);
    freeSpaceAndCache(requestUrl, JSON.stringify(apiResponse));
}

/**
 * Return true if the given value has a non-array object type.
 */
function isNonArrayObject(value: unknown): boolean {
    return (
        typeof value === 'object'
        && value !== null
        && !(value instanceof Array)
    );
}

/**
 * Fetch the response for the given MyakuWeb API request URL.
 *
 * Note that this function does not use responses manually cached in session
 * storage, but the browser may return a cached response for the fetch call if
 * approriate.
 *
 * @param requestUrl - MyakuWeb API request URL to fetch.
 *
 * @returns A Promise that resolves to the ApiResponse for the request URL if
 * the request was successful, and rejects with an Error if the request failed.
 */
async function fetchApiRequest(requestUrl: string): Promise<ApiResponse> {
    const response = await fetch(requestUrl);
    if (!response.ok) {
        throw new Error(
            `Request for ${requestUrl} failed with status: `
            + `${response.status} - ${response.statusText}`
        );
    }

    const responseJson = await response.json();
    if (!isNonArrayObject(responseJson)) {
        throw new Error(
            `Response JSON for ${requestUrl} request is not a non-array `
            + `object: "${JSON.stringify(responseJson)}"`
        );
    }

    if (responseJson[API_RESPONSE_ERROR_KEY] !== undefined) {
        throw new Error(
            `Response JSON for ${requestUrl} request contains errors: `
            + `"${JSON.stringify(responseJson)}"`
        );
    }

    return {
        expireTime: getExpireTime(response),
        json: responseJson,
    };
}

/**
 * Fetch the JSON for a MyakuWeb API request URL.
 *
 * Instead of making a fetch request for the URL, will use a manually cached
 * response for the request URL from session storage if a response exists for
 * the URL there that is not expired.
 *
 * Before returning the JSON for a response, converts any ISO datetime strings
 * in the response to javascript Date objects.
 *
 * @param url - MyakuWeb API request URL to fetch.
 *
 * @returns A Promise that resolves to the JSON for the request URL if the
 * request was successful, and rejects with an Error if the request failed.
 */
async function fetchApiJson(url: string): Promise<unknown> {
    var responseJson: unknown | null = null;
    const apiResponseStr = window.sessionStorage.getItem(url);
    if (apiResponseStr !== null) {
        const apiResponse = JSON.parse(apiResponseStr) as ApiResponse;
        if (!isExpired(apiResponse)) {
            responseJson = apiResponse.json;
        }
    }

    if (responseJson === null) {
        const apiResponse = await fetchApiRequest(url);
        cacheApiResponse(url, apiResponse);
        responseJson = apiResponse.json;
    }

    recursivelyTransform(
        responseJson, convertIsoFormatToDate, isDatetimeKey
    );
    return responseJson;
}

/**
 * Make a MyakuWeb API request to get the search results for the given search.
 *
 * @param search - Search to make the search results API request for.
 *
 * @returns A Promise that resolves to the search result page data for the
 * search from the API response, and that rejects with an Error if the request
 * failed.
 */
export async function getSearchResultPage(
    search: Search
): Promise<SearchResultPage> {
    var requestUrl = (
        '/api/search'
        + `?q=${search.query}`
        + `&p=${search.pageNum}`
    );
    var response = await (
        fetchApiJson(requestUrl) as Promise<SearchResultPageResponse>
    );

    return {
        search: {
            query: search.query,
            pageNum: response.pageNum,
        },
        totalResults: response.totalResults,
        hasNextPage: response.hasNextPage,
        maxPageReached: response.maxPageReached,
        results: response.articleResults,
    };
}

/**
 * Make a MyakuWeb API request to get the search resources for the given search
 * query.
 *
 * @param query - Search query to make the search resources API request for.
 *
 * @returns A Promise that resolves to the search resources data for the
 * query from the API response, and that rejects with an Error if the request
 * failed.
 */
export async function getSearchResources(
    query: string
): Promise<SearchResources> {
    var requestUrl = `/api/resource-links?q=${query}`;
    var response = await (
        fetchApiJson(requestUrl) as Promise<ResourceLinksResponse>
    );

    return {
        query: query,
        resourceLinkSets: response.resourceLinkSets,
    };
}

/**
 * Make MyakuWeb API requests to get both search results and search resources
 * for the given search.
 *
 * @param query - Search to make the API requests for.
 *
 * @returns A Promise that resolves to an array with the search result page and
 * search response data for the search from the API responses, and that rejects
 * with an Error if any of the requests failed.
 */
export async function getSearchWithResources(
    search: Search
): Promise<[SearchResultPage, SearchResources]> {
    return Promise.all([
        getSearchResultPage(search),
        getSearchResources(search.query),
    ]);
}
