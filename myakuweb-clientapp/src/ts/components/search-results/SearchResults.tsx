/**
 * Queried search results display component.
 * @module ts/components/search-results/SearchResults
 */

import History from 'history';
import React from 'react';
import SearchResourceTiles from
    'ts/components/search-results/SearchResourceTiles';
import SearchResultPageTiles from
    'ts/components/search-results/SearchResultPageTiles';
import { scrollToTop } from 'ts/app/utils';

import {
    Search,
    SearchResources,
    SearchResultPage,
} from 'ts/types/types';
import {
    getSearchFromLocation,
    getSearchUrl,
    isSearchEqual,
} from 'ts/app/search';
import {
    getSearchResultPage,
    getSearchWithResources,
} from 'ts/app/apiRequests';

const enum SearchType {
    NewQuery = 'query',
    NewPage = 'page',
}

interface SearchResultsProps {
    onSearchQueryChange: (newValue: string) => void;
    onLoadingNewSearchQueryChange: (loading: boolean) => void;
    location: History.Location;
    history: History.History;
}
type Props = SearchResultsProps;

interface SearchResultsState {
    requestedSearch: Search | null;
    requestedSearchType: SearchType | null;
    loadedSearch: Search | null;
    searchResultPage: SearchResultPage | null;
    searchResources: SearchResources | null;
    showResultsLoadingTiles: boolean;
    showResourcesLoadingTiles: boolean;
    showPageNavLoadingIndicator: boolean;
}
type State = SearchResultsState;

type LoadingTileState = (
    Pick<State, 'showResultsLoadingTiles' | 'showResourcesLoadingTiles'>
);

type RequestedSearchState = (
    Pick<State, 'requestedSearch' | 'requestedSearchType'>
);

type SearchResponseState = Omit<State, 'requestedSearchType'>;

type SearchResponse = SearchResultPage | [SearchResultPage, SearchResources];

const SHOW_LOADING_TIMEOUT = 100;  // in milliseconds


function getDocumentTitle(search: Search): string {
    return `${search.query} - Page ${search.pageNum} - Myaku`;
}

function isSearchLoading(search: Search, state: State, props: Props): boolean {
    const urlSearch = getSearchFromLocation(props.location);
    if (
        !isSearchEqual(search, urlSearch)
        || isSearchEqual(search, state.loadedSearch)
    ) {
        return false;
    }
    return true;
}

class SearchResults extends React.Component<Props, State> {
    private _historyUnlistenCallback: History.UnregisterCallback | null;

    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this._historyUnlistenCallback = null;
        this.state = {
            requestedSearch: null,
            requestedSearchType: null,
            loadedSearch: null,
            searchResultPage: null,
            searchResources: null,
            showResultsLoadingTiles: false,
            showResourcesLoadingTiles: false,
            showPageNavLoadingIndicator: false,
        };
    }

    componentDidMount(): void {
        this.handleLocationChange();

        this._historyUnlistenCallback = this.props.history.listen(
            this.handleHistoryChange
        );
    }

    componentDidUpdate(): void {
        this.handleLocationChange();
    }

    componentWillUnmount(): void {
        if (this._historyUnlistenCallback !== null) {
            this._historyUnlistenCallback();
        }
    }

    bindEventHandlers(): void {
        this.handleHistoryChange = this.handleHistoryChange.bind(this);
        this.handleSearchResponseLoaded = (
            this.handleSearchResponseLoaded.bind(this)
        );
    }

    disableLoadingIndicators(): void {
        if (
            this.state.showResultsLoadingTiles
            || this.state.showResourcesLoadingTiles
            || this.state.showPageNavLoadingIndicator
        ) {
            this.setState({
                showResultsLoadingTiles: false,
                showResourcesLoadingTiles: false,
                showPageNavLoadingIndicator: false,
            });
        }
    }

    handleHistoryChange(
        location: History.Location, action: History.Action
    ): void {
        if (action !== 'POP') {
            return;
        }

        const search = getSearchFromLocation(location);
        setTimeout(
            this.getShowTilesLoadingHandler(search), SHOW_LOADING_TIMEOUT
        );
    }

    handleLocationChange(): void {
        const search = getSearchFromLocation(this.props.location);
        if (search.query.length === 0) {
            // Redirect to start page because search is invalid (no query)
            this.props.history.replace('/');
            return;
        }

        if (isSearchEqual(search, this.state.loadedSearch)) {
            this.disableLoadingIndicators();
        }

        if (!isSearchEqual(search, this.state.requestedSearch)) {
            this.handleSearchRequest(search);
        }
    }

    handleSearchRequest(search: Search): void {
        function updateState(
            this: SearchResults, prevState: State, props: Props
        ): RequestedSearchState {
            var searchType: SearchType;
            var showLoadingHandler: () => void;
            if (
                prevState.loadedSearch !== null
                && search.query === prevState.loadedSearch.query
            ) {
                searchType = SearchType.NewPage;
                showLoadingHandler = this.getShowPageNavLoadingHandler(search);
                getSearchResultPage(search).then(
                    this.getSearchResponseHandler(search)
                );
            } else {
                searchType = SearchType.NewQuery;
                showLoadingHandler = this.getShowTilesLoadingHandler(search);
                getSearchWithResources(search).then(
                    this.getSearchResponseHandler(search)
                );
            }

            props.onSearchQueryChange(search.query);
            setTimeout(showLoadingHandler, SHOW_LOADING_TIMEOUT);
            return {
                requestedSearch: search,
                requestedSearchType: searchType,
            };
        }

        this.setState(updateState.bind(this));
    }

    getShowTilesLoadingHandler(loadingSearch: Search): () => void {
        function handler(this: SearchResults): void {
            function updateState(
                prevState: State, props: Props
            ): LoadingTileState | null {
                if (!isSearchLoading(loadingSearch, prevState, props)) {
                    return null;
                }

                var showResourcesLoadingTiles = true;
                if (
                    prevState.loadedSearch !== null
                    && loadingSearch.query === prevState.loadedSearch.query
                ) {
                    showResourcesLoadingTiles = false;
                }
                props.onLoadingNewSearchQueryChange(true);
                return {
                    showResultsLoadingTiles: true,
                    showResourcesLoadingTiles: showResourcesLoadingTiles,
                };
            }

            this.setState(updateState);
        }

        return handler.bind(this);
    }

    getShowPageNavLoadingHandler(loadingSearch: Search): () => void {
        function handler(this: SearchResults): void {
            function updateState(
                prevState: State, props: Props
            ): Pick<State, 'showPageNavLoadingIndicator'> | null {
                if (!isSearchLoading(loadingSearch, prevState, props)) {
                    return null;
                }

                return {
                    showPageNavLoadingIndicator: true,
                };
            }

            this.setState(updateState);
        }

        return handler.bind(this);
    }

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

                document.title = getDocumentTitle(searchResultPage.search);
                props.onSearchQueryChange(searchResultPage.search.query);
                props.onLoadingNewSearchQueryChange(false);
                return {
                    requestedSearch: searchResultPage.search,
                    loadedSearch: searchResultPage.search,
                    searchResultPage: searchResultPage,
                    searchResources: searchResources,
                    showResultsLoadingTiles: false,
                    showResourcesLoadingTiles: false,
                    showPageNavLoadingIndicator: false,
                };
            }

            this.setState(updateState, this.handleSearchResponseLoaded);
        }

        return handler.bind(this);
    }

    handleSearchResponseLoaded(): void {
        const urlSearch = getSearchFromLocation(this.props.location);
        if (
            this.state.loadedSearch !== null
            && !isSearchEqual(urlSearch, this.state.loadedSearch)
        ) {
            this.props.history.replace(getSearchUrl(this.state.loadedSearch));
        }

        scrollToTop();
    }

    getLoadingPageNum(): number | null {
        if (
            this.state.requestedSearch !== null
            && this.state.showPageNavLoadingIndicator
            && !this.state.showResultsLoadingTiles
            && !this.state.showResourcesLoadingTiles
        ) {
            return this.state.requestedSearch.pageNum;
        } else {
            return null;
        }
    }

    getRenderSearchResultPage(): SearchResultPage | null {
        if (this.state.showResultsLoadingTiles) {
            return null;
        }
        return this.state.searchResultPage;
    }

    getRenderSearchResources(): SearchResources | null {
        if (this.state.showResourcesLoadingTiles) {
            return null;
        }
        return this.state.searchResources;
    }

    render(): React.ReactElement {
        return (
            <React.Fragment>
                <SearchResultPageTiles
                    requestedSearch={this.state.requestedSearch}
                    loadedSearch={this.state.loadedSearch}
                    resultPage={this.getRenderSearchResultPage()}
                    loadingPageNum={this.getLoadingPageNum()}
                />
                <SearchResourceTiles
                    resources={this.getRenderSearchResources()}
                />
            </React.Fragment>
        );
    }
}

export default SearchResults;
