/**
 * Functions for working with search options and search queries.
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
 * with a page number of 1.
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

/**
 * Returns true if the given two Search objects are equivalent.
 */
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

/**
 * Get the page number parameter value from the given URL search params.
 *
 * @param urlParams - URL search params to get the page number parameter value
 * from.
 *
 * @returns The page number parameter value if the page number key is in the
 * given URL search params and its value is a valid page number.
 * Otherwise, null.
 */
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

/**
 * Get the search query parameter value from the given location.
 *
 * @param location - Location to get the search query parameter value from.
 *
 * @returns The search query parameter value if the search query is specified
 * in the given location.
 * Otherwise, null.
 */
export function getSearchQueryFromLocation(
    location: History.Location
): string | null {
    const urlParams = new URLSearchParams(location.search);
    return urlParams.get(SEARCH_URL_PARAMS.query);
}

/**
 * Get the search options values for all locations.
 *
 * No search option is currently specified via locations, so this function
 * currently just returns null for all search option values, but in the future,
 * it may return different values based on a given location.
 *
 * @returns The search options values for all locations (i.e. all null values).
 */
export function getSearchOptionsFromLocation(): AllNullable<SearchOptions> {
    return {
        kanaConvertType: null,
    };
}

/**
 * Replace any null values in the given search options with default values.
 *
 * @param options - A search options object with some keys possibly having null
 * values.
 *
 * @returns A copy of the given search options object with all null values
 * replaced with the default value for that search option key.
 */
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

/**
 * Get the search specified by a given location.
 *
 * If the query parameter is missing in the location, uses an empty string
 * instead.
 * If the page number is missing in the location, uses 1 instead.
 */
export function getSearchFromLocation(location: History.Location): Search {
    const urlParams = new URLSearchParams(location.search);
    return {
        query: urlParams.get(SEARCH_URL_PARAMS.query) || '',
        pageNum: getPageNumUrlParam(urlParams) || 1,
    };
}

/**
 * Get a connection to the MyakuWeb IndexedDB database.
 *
 * @returns A Promise that resolves to the database connection.
 *
 * Note that the Promise will reject if no IndexedDB was available.
 */
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

/**
 * Get the search options store of the MyakuWeb IndexedDB database.
 *
 * @param mode - The read-write mode to set for the returned search options
 * store.
 *
 * @returns A Promise that resolves to the search options store.
 *
 * Note that the Promise will reject if no IndexedDB was available.
 */
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

/**
 * Load the search options stored for the user in the MyakuWeb IndexedDB
 * database.
 *
 * @returns A Promise that resolves to the search options stored for the user
 * with null values set for any option keys that did not have a value stored in
 * the database.
 *
 * Note that the Promise will reject if no IndexedDB was available.
 */
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

/**
 * Set a search option value for the user in the MyakuWeb IndexedDB search
 * options store.
 *
 * @param option - Search option key to set a value for.
 * @param value - Value to set for the given search option key.
 *
 * @returns A Promise that resolves to the search options stored for the user
 * after setting the given key-value pair in the store. Null values will be set
 * for any option keys that did not have a value stored in the database.
 *
 * Note that the Promise will reject if no IndexedDB was available.
 */
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
