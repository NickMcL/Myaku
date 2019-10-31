/**
 * Functions for working with search options and search queries.
 * @module ts/app/search-options
 */

import History from 'history';

import {
    AllNullable,
    Search,
    SearchOptions,
    isSearchOption,
} from 'ts/types/types';

const SEARCH_URL_PARAMS = {
    query: 'q',
    pageNum: 'p',
    kanaConvertType: 'conv',
};

const DEFAULT_SEARCH_OPTIONS: SearchOptions = {
    kanaConvertType: 'hira',
};

const NULL_SEARCH_OPTIONS: AllNullable<SearchOptions> = {
    kanaConvertType: null,
};

const MYAKUWEB_INDEXEDDB_NAME = 'MyakuWeb';
const MYAKUWEB_INDEXEDB_VERSION = 1;
const SEARCH_OPTIONS_STORE_NAME = 'SearchOptions';
const SEARCH_OPTIONS_STORE_KEY = 'UserSearchOptions';

/**
 * Get a URL for the search results page for the given search.
 *
 * @param search - If a Search object, a search URL using the object's
 * parameters. If a string, a search URL using that string as the search query
 * with default search options.
 *
 * @returns A URL for the search results page for the given search.
 */
export function getSearchUrl(search: Search | string): string {
    if (typeof search === 'string') {
        return `/search/?q=${search}`;
    }

    return (
        '/search/'
        + `?q=${search.query}`
        + `&p=${search.pageNum}`
    );
}

export function isSearchEqual(
    search: Search, cmpSearch: Search | null
): boolean {
    if (cmpSearch === null) {
        return false;
    }

    if (
        search.query !== cmpSearch.query
        || search.pageNum !== cmpSearch.pageNum
    ) {
        return false;
    }
    return true;
}

function getPageNumUrlParam(urlParams: URLSearchParams): number | null {
    const pageNumParamValue = urlParams.get(SEARCH_URL_PARAMS.pageNum);
    if (pageNumParamValue === null) {
        return null;
    }

    const pageNum = Number(pageNumParamValue);
    if (Number.isInteger(pageNum) && pageNum > 0) {
        return pageNum;
    } else {
        return null;
    }
}

export function getSearchQueryFromLocation(
    location: History.Location
): string | null {
    const urlParams = new URLSearchParams(location.search);
    return urlParams.get(SEARCH_URL_PARAMS.query);
}

export function getSearchOptionsFromLocation(): AllNullable<SearchOptions> {
    return {
        kanaConvertType: null,
    };
}

export function applyDefaultSearchOptions(
    options: AllNullable<SearchOptions>
): SearchOptions {
    var defaultsAppliedOptions: SearchOptions = {...DEFAULT_SEARCH_OPTIONS};
    for (const optionKey of Object.keys(defaultsAppliedOptions)) {
        if (!isSearchOption(optionKey)) {
            continue;
        }

        const option = options[optionKey];
        if (option !== null) {
            defaultsAppliedOptions[optionKey] = option;
        }
    }
    return defaultsAppliedOptions;
}

export function getSearchFromLocation(location: History.Location): Search {
    const urlParams = new URLSearchParams(location.search);
    return {
        query: urlParams.get(SEARCH_URL_PARAMS.query) || '',
        pageNum: getPageNumUrlParam(urlParams) || 1,
    };
}

async function connectToMyakuWebIndexedDb(): Promise<IDBDatabase> {
    return new Promise(function(resolve, reject): void {
        var openRequest = window.indexedDB.open(
            MYAKUWEB_INDEXEDDB_NAME, MYAKUWEB_INDEXEDB_VERSION
        );
        openRequest.onerror = (): void => reject(openRequest.error);
        openRequest.onsuccess = (): void => resolve(openRequest.result);

        openRequest.onupgradeneeded = function(
            event: IDBVersionChangeEvent
        ): void {
            var db = (event.target as IDBOpenDBRequest).result;
            try {
                db.deleteObjectStore(SEARCH_OPTIONS_STORE_NAME);
            } catch (e) {
                if (e.name !== 'NotFoundError') {
                    throw e;
                }
            }

            db.createObjectStore(SEARCH_OPTIONS_STORE_NAME);
        };
    });
}

async function getSearchOptionsStore(
    mode: 'readonly' | 'readwrite'
): Promise<IDBObjectStore> {
    var db = await connectToMyakuWebIndexedDb();
    var transaction = db.transaction(SEARCH_OPTIONS_STORE_NAME, mode);
    transaction.oncomplete = (): void => db.close();
    transaction.onerror = (): void => db.close();
    transaction.onabort = (): void => db.close();

    return transaction.objectStore(SEARCH_OPTIONS_STORE_NAME);
}

export async function loadUserSearchOptions(
): Promise<AllNullable<SearchOptions>> {
    var store = await getSearchOptionsStore('readonly');
    var getRequest = store.get(SEARCH_OPTIONS_STORE_KEY);
    return new Promise(function(resolve, reject): void {
        getRequest.onsuccess = function(): void {
            if (getRequest.result === undefined) {
                resolve({...NULL_SEARCH_OPTIONS});
            } else {
                resolve(getRequest.result);
            }
        };
        getRequest.onerror = (): void => reject(getRequest.error);
    });
}

export async function setUserSearchOption<T extends keyof SearchOptions>(
    option: T, value: SearchOptions[T]
): Promise<AllNullable<SearchOptions>> {
    var storedOptions = await loadUserSearchOptions();
    storedOptions[option] = value;

    var store = await getSearchOptionsStore('readwrite');
    var putRequest = store.put(storedOptions, SEARCH_OPTIONS_STORE_KEY);
    putRequest.onerror = function(): void {
        throw putRequest.error;
    };
    return storedOptions;
}
