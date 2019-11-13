/**
 * SearchResults component module. See [[SearchResults]].
 */

import History from 'history';
import React from 'react';
import SearchFailedTile from 'ts/components/search-results/SearchFailedTile';
import SearchResourceTiles from
    'ts/components/search-results/SearchResourceTiles';
import SearchResultPageTiles from
    'ts/components/search-results/SearchResultPageTiles';

import {
    Search,
    SearchResources,
    SearchResultPage,
} from 'ts/types/types';
import {
    getSearchFromLocation,
    isSearchEqual,
} from 'ts/app/search';
import {
    getSearchResultPage,
    getSearchWithResources,
} from 'ts/app/apiRequests';

/** Props for the [[SearchResults]] component. */
interface SearchResultsProps {
    /**
     * Callback for indicating when a new search query starts and finishes
     * loading.
     */
    onLoadingNewSearchQueryChange: (loading: boolean) => void;

    /**
     * Current page location for the app.
     *
     * The query, page number, and other options for the search made by the
     * component is determined by the URL search params of this location.
     */
    location: History.Location;

    /**
     * History object currently being used by the app.
     *
     * Used to redirect back to the start page if the URL search params for the
     * given location are invalid.
     *
     * Also used to listen for history changes so that search errors can be
     * cleared on page change.
     */
    history: History.History;
}
type Props = SearchResultsProps;

/** State for the [[SearchResults]] component. */
interface SearchResultsState {
    /**
     * Last search that an API request was made for by the component.
     *
     * If null, no API request for a search has been made yet.
     */
    requestedSearch: Search | null;

    /**
     * Last search whose results were fully loaded from the search API by the
     * component.
     *
     * If null, no search has been fully loaded yet.
     */
    loadedSearch: Search | null;

    /**
     * Last search result page loaded from the search API by the component.
     *
     * If null, no search result page has been loaded yet.
     */
    searchResultPage: SearchResultPage | null;

    /**
     * Last search resources loaded from the search API by the component.
     *
     * If null, no search resources have been loaded yet.
     */
    searchResources: SearchResources | null;

    /**
     * If true, a new search result page is being loaded, so loading tiles
     * should be displayed in place of search result tiles for the component.
     *
     * If false, search result tiles for the data from the current
     * searchResultPage state value should be displayed.
     */
    showLoadingNewPage: boolean;

    /**
     * If true, a search with a different query than the previous search is
     * being loaded, so loading tiles should be displayed in place of search
     * result and search resources tiles for the component.
     *
     * If false, search result and search resource tiles for the data
     * from the current searchResultPage and searchResources state values
     * should be displayed.
     */
    showLoadingNewQuery: boolean;

    /**
     * If true, a tile indicating that the last search API request failed
     * should be displayed instead of search result tiles.
     */
    searchFailed: boolean;

    /**
     * The error message for the current search failure.
     *
     * If null, there is no current search failure.
     */
    searchFailErrorMessage: string | null;
}
type State = SearchResultsState;

type LoadingTileState = (
    Pick<State, 'showLoadingNewPage' | 'showLoadingNewQuery'>
);

type SearchErrorState = Pick<State, 'searchFailed' | 'searchFailErrorMessage'>;

type SearchResponseState = (
    Omit<State, 'requestedSearch' | 'searchFailed' | 'searchFailErrorMessage'>
);

type SearchResponse = SearchResultPage | [SearchResultPage, SearchResources];

/**
 * Time in milliseconds that should be waited between a new search API request
 * being made and loading indicators being displayed to the user.
 *
 * This timeout is in place so that API requests that are served very quickly
 * don't cause the loading indicators to flash for a split second before
 * showing the loaded content. This results in a snappier feeling to the app.
 */
const SHOW_LOADING_TIMEOUT = 100;


/**
 * Get the document title that should be used for a search result page for the
 * given search.
 */
function getDocumentTitle(search: Search): string {
    return `${search.query} - Page ${search.pageNum} - Myaku`;
}

/**
 * Based on the given props and state, return true if the given search is
 * currently being loaded by the component. Otherwise, return false.
 */
function isSearchLoading(search: Search, state: State, props: Props): boolean {
    const urlSearch = getSearchFromLocation(props.location);
    if (
        state.searchFailed
        || !isSearchEqual(search, urlSearch)
        || isSearchEqual(search, state.loadedSearch)
    ) {
        return false;
    }
    return true;
}

/**
 * Component for displaying the results of searchs made in app.
 *
 * @remarks
 * See [[SearchResultsProps]] and [[SearchResultsState]] for props and state
 * details.
 */
class SearchResults extends React.Component<Props, State> {
    /**
     * Callback to unregister the history change listener registered by this
     * component on mount.
     *
     * This callback is saved in an instance variable on component mount so
     * that it can be called later during component unmount.
     */
    private _historyUnlistenCallback: History.UnregisterCallback | null;

    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this._historyUnlistenCallback = null;
        this.state = {
            requestedSearch: null,
            loadedSearch: null,
            searchResultPage: null,
            searchResources: null,
            showLoadingNewPage: false,
            showLoadingNewQuery: false,
            searchFailed: false,
            searchFailErrorMessage: null,
        };
    }

    /**
     * Does two tasks on mount:
     *   1. Register the history change listener for the component.
     *   2. Start loading result data for the search specified by the given
     *   location prop.
     */
    componentDidMount(): void {
        this.handleSearchDataLoad();

        this._historyUnlistenCallback = this.props.history.listen(
            this.handleHistoryChange
        );
    }

    /**
     * Starts loading result data for the search specified by the given
     * location prop if it is not already loading or already loaded.
     */
    componentDidUpdate(): void {
        this.handleSearchDataLoad();
    }

    /**
     * Unregister the history change listener for the component on unmount.
     */
    componentWillUnmount(): void {
        this._historyUnlistenCallback?.();
    }

    /**
     * Bind "this" for the event handlers used by the component.
     */
    bindEventHandlers(): void {
        this.handleHistoryChange = this.handleHistoryChange.bind(this);
    }

    /**
     * Force any loading indicators being displayed by the component to stop
     * being displayed.
     */
    disableLoadingIndicators(): void {
        function updateState(
            prevState: State, props: Props
        ): LoadingTileState | null {
            if (
                !prevState.showLoadingNewPage && !prevState.showLoadingNewQuery
            ) {
                return null;
            }

            props.onLoadingNewSearchQueryChange(false);
            return {
                showLoadingNewPage: false,
                showLoadingNewQuery: false,
            };
        }

        this.setState(updateState);
    }

    /**
     * Stop displaying the search failed tile if it is currently displaying.
     */
    clearSearchError(): void {
        function updateState(prevState: State): SearchErrorState | null {
            if (!prevState.searchFailed) {
                return null;
            }

            return {
                searchFailed: false,
                searchFailErrorMessage: null,
            };
        }

        this.setState(updateState);
    }

    /**
     * Clear the current search error if there is one on every history change.
     */
    handleHistoryChange(): void {
        this.clearSearchError();
    }

    /**
     * Start loading result data for the search specified by the given
     * location prop.
     *
     * If the search is invalid (i.e. no query is provided), redirects the app
     * to the start page.
     *
     * If the search is already loading or already loaded, does NOT start
     * loading the search again.
     *
     * Additionally, sets the document title to match the search, and disables
     * loading indicators if they are running while no search is being loaded.
     */
    handleSearchDataLoad(): void {
        const search = getSearchFromLocation(this.props.location);
        if (search.query.length === 0) {
            // Redirect to start page because search is invalid (no query)
            this.props.history.replace('/');
            return;
        }

        if (
            this.state.searchFailed
            || isSearchEqual(search, this.state.loadedSearch)
        ) {
            this.disableLoadingIndicators();
        }

        if (
            !this.state.searchFailed
            && !isSearchEqual(search, this.state.requestedSearch)
        ) {
            document.title = getDocumentTitle(search);
            this.handleSearchRequest(search);
        }
    }

    /**
     * Make an async search API request for the given search.
     *
     * Will request search resources as well if the given search has a query
     * different than the currently displaying search.
     *
     * Additionally, sets a timeout to show loading indicators for the search
     * after [[SHOW_LOADING_TIMEOUT]] milliseconds.
     */
    handleSearchRequest(search: Search): void {
        function updateState(
            this: SearchResults, prevState: State
        ): Pick<State, 'requestedSearch'> {
            var searchResponsePromise: Promise<SearchResponse>;
            if (
                prevState.loadedSearch !== null
                && search.query === prevState.loadedSearch.query
            ) {
                searchResponsePromise = getSearchResultPage(search);
            } else {
                searchResponsePromise = getSearchWithResources(search);
            }
            searchResponsePromise.then(
                this.getSearchResponseHandler(search),
                this.getSearchFailureHandler(search)
            );

            setTimeout(
                this.getShowTilesLoadingHandler(search), SHOW_LOADING_TIMEOUT
            );
            return {
                requestedSearch: search,
            };
        }

        this.setState(updateState.bind(this));
    }

    /**
     * Get an error handler function that will set the requested search as
     * failed in the component state ONLY IF the requested search state value
     * at the time the handler runs matches the given search parameter.
     */
    getSearchFailureHandler(search: Search): (error: Error) => void {
        function handler(this: SearchResults, error: Error): void {
            function updateState(prevState: State, props: Props): (
                State | null
            ) {
                if (!isSearchEqual(search, prevState.requestedSearch)) {
                    return null;
                }

                props.onLoadingNewSearchQueryChange(false);
                return {
                    searchFailed: true,
                    searchFailErrorMessage: `${error.name}: ${error.message}`,
                    requestedSearch: null,
                    loadedSearch: null,
                    searchResultPage: null,
                    searchResources: null,
                    showLoadingNewPage: false,
                    showLoadingNewQuery: false,
                };
            }

            this.setState(updateState);
        }

        return handler.bind(this);
    }

    /**
     * Get a handler function that will set loading tiles to display in the
     * component state ONLY IF the given search parameter matches the search
     * currently being loaded by the component at the time the handler runs.
     */
    getShowTilesLoadingHandler(loadingSearch: Search): () => void {
        function handler(this: SearchResults): void {
            function updateState(
                prevState: State, props: Props
            ): LoadingTileState | null {
                if (!isSearchLoading(loadingSearch, prevState, props)) {
                    return null;
                }

                var showLoadingNewQuery = true;
                if (
                    prevState.loadedSearch !== null
                    && loadingSearch.query === prevState.loadedSearch.query
                ) {
                    showLoadingNewQuery = false;
                }
                props.onLoadingNewSearchQueryChange(showLoadingNewQuery);
                return {
                    showLoadingNewPage: true,
                    showLoadingNewQuery: showLoadingNewQuery,
                };
            }

            this.setState(updateState);
        }

        return handler.bind(this);
    }

    /**
     * Get a search API response handler function that will set the search
     * results loaded from the API as the results to display in the component
     * state ONLY IF the requested search state value at the time the handler
     * runs matches the given search parameter.
     */
    getSearchResponseHandler(
        search: Search
    ): (response: SearchResponse) => void {
        function handler(this: SearchResults, response: SearchResponse): void {
            function updateState(prevState: State, props: Props): (
                SearchResponseState | null
            ) {
                if (!isSearchEqual(search, prevState.requestedSearch)) {
                    return null;
                }

                var searchResultPage;
                var searchResources;
                if (response instanceof Array) {
                    searchResultPage = response[0];
                    searchResources = response[1];
                } else {
                    searchResultPage = response;
                    searchResources = prevState.searchResources;
                }

                props.onLoadingNewSearchQueryChange(false);
                return {
                    loadedSearch: searchResultPage.search,
                    searchResultPage: searchResultPage,
                    searchResources: searchResources,
                    showLoadingNewPage: false,
                    showLoadingNewQuery: false,
                };
            }

            this.setState(updateState);
        }

        return handler.bind(this);
    }

    /**
     * Get the total result count for the current search results being
     * displayed.
     *
     * If null is returned, it means the component is in the middle of loading
     * a new search query, so the total result count is currently unknown.
     */
    getTotalSearchResultCount(): number | null {
        if (
            this.state.searchResultPage === null
            || this.state.showLoadingNewQuery
        ) {
            return null;
        }
        return this.state.searchResultPage.totalResults;
    }

    /**
     * Get the search result page data that should be rendered.
     *
     * If null is returned, it means that loading tiles should be displayed
     * in place of search result page data currently.
     */
    getRenderSearchResultPage(): SearchResultPage | null {
        if (this.state.showLoadingNewPage) {
            return null;
        }
        return this.state.searchResultPage;
    }

    /**
     * Get the search resource page data that should be rendered.
     *
     * If null is returned, it means that loading tiles should be displayed in
     * place of search resource data currently.
     */
    getRenderSearchResources(): SearchResources | null {
        if (this.state.showLoadingNewQuery) {
            return null;
        }
        return this.state.searchResources;
    }

    render(): React.ReactElement {
        if (this.state.searchFailed) {
            return <SearchFailedTile />;
        }

        return (
            <React.Fragment>
                <SearchResultPageTiles
                    requestedSearch={this.state.requestedSearch}
                    totalResults={this.getTotalSearchResultCount()}
                    resultPage={this.getRenderSearchResultPage()}
                />
                <SearchResourceTiles
                    resources={this.getRenderSearchResources()}
                />
            </React.Fragment>
        );
    }
}

export default SearchResults;
