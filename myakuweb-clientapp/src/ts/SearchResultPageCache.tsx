/**
 * @module SearchResultPageCache
 */

import {
    SEARCH_OPTIONS,
    Search,
    SearchResultPage,
} from './types';


/**
 * A cache for the pages previously downloaded for a given search.
 *
 * Only stores the pages for one search at a time. If a page for a new search
 * is added to the cache, the cache is first cleared of the pages from the
 * previous search.
 *
 * Using this prevents redownloading pages as a user goes back and forth
 * between the pages for a search query.
 */
export default class SearchResultPageCache {
    private _search: Search | null;
    private _pageCache: Map<number, SearchResultPage>;

    /**
     * Initialize the cache with no pages in it.
     */
    constructor() {
        this._search = null;
        this._pageCache = new Map();
    }

    /**
     * Set the search result page for the given search in the cache. Clears any
     * previous pages in the cache if the given search is different than the
     * current search being cached.
     *
     * @param search - The search made to get the given results page.
     * @param resultPage - The results page to cache.
     */
    set(search: Search, resultPage: SearchResultPage): void {
        if (this._isNewSearch(search)) {
            this._search = search;
            this._pageCache.clear();
        }
        this._pageCache.set(search.pageNum, resultPage);
    }

    /**
     * Get the search result page from the cache for the given search.
     *
     * @param search - The search whose result page to get from the cache.
     *
     * @returns The cached search result page for the search if it's in the
     * cache, or null if either the page isn't in the cache or the current
     * search being cached is different than the given search.
     */
    get(search: Search): SearchResultPage | null {
        if (!this.has(search)) {
            return null;
        }
        return this._pageCache.get(search.pageNum) || null;
    }

    /**
     * Check if the search result page for the given search is in the cache.
     *
     * @param search - The search whose result page to check for in the cache.
     *
     * @returns True if the search result page for the given search is in the
     * cache, False otherwise.
     */
    has(search: Search): boolean {
        if (
            this._isNewSearch(search)
            || !this._pageCache.has(search.pageNum)
        ) {
            return false;
        }
        return true;
    }

    /**
     * Force clears all pages stored in the cache.
     */
    clear(): void {
        this._search = null;
        this._pageCache.clear();
    }

    /**
     * Determine if the given search is different that the current search being
     * cached.
     *
     * @param search - The search to compare to the current search.
     *
     * @returns True if the given search is different than the current
     * search being cache, False otherwise.
     */
    private _isNewSearch(search: Search): boolean {
        if (this._search === null) {
            return true;
        }

        if (this._search.query !== search.query) {
            return true;
        }

        for (const option of SEARCH_OPTIONS) {
            if (this._search.options[option] !== search.options[option]) {
                return true;
            }
        }

        return false;
    }
}
