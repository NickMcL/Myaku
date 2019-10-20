/* Functions for making requests to MyakuWeb API */

import { recursivelyApply } from './utils';
import {
    PrimativeType,
    ResourceLinksResponse,
    SearchOptions,
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

    return fetch(request, init)
        .then(async response => response.json())
        .then(function(responseJson) {
            recursivelyApply(
                responseJson, convertIsoFormatToDate, isDatetimeKey
            );
            return responseJson;
        });
}

export async function getSessionSearchOptions(
): Promise<SessionSearchOptionsResponse> {
    return fetchJson('/api/session-search-options') as (
        Promise<SessionSearchOptionsResponse>
    );
}

export async function getSearchResultPage(
    query: string, pageNum: number, searchOptions: SearchOptions
): Promise<SearchResultPageResponse> {
    return fetchJson(
        '/api/search'
        + `?q=${query}&p=${pageNum}&conv=${searchOptions.kanaConvertType}`
    ) as Promise<SearchResultPageResponse>;
}

export async function getResourceLinks(
    query: string, searchOptions: SearchOptions
): Promise<ResourceLinksResponse> {
    return fetchJson(
        '/api/search'
        + `?q=${query}&conv=${searchOptions.kanaConvertType}`
    ) as Promise<ResourceLinksResponse>;
}
