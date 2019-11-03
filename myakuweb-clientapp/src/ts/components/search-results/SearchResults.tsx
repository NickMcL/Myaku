/**
 * Queried search results display component.
 * @module ts/components/search-results/SearchResults
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

interface SearchResultsProps {
    onLoadingNewSearchQueryChange: (loading: boolean) => void;
    location: History.Location;
    history: History.History;
}
type Props = SearchResultsProps;

interface SearchResultsState {
    requestedSearch: Search | null;
    loadedSearch: Search | null;
    searchResultPage: SearchResultPage | null;
    searchResources: SearchResources | null;
    showLoadingNewPage: boolean;
    showLoadingNewQuery: boolean;
    searchFailed: boolean;
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

const SHOW_LOADING_TIMEOUT = 100;  // in milliseconds


function getDocumentTitle(search: Search): string {
    return `${search.query} - Page ${search.pageNum} - Myaku`;
}

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

class SearchResults extends React.Component<Props, State> {
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

    componentDidMount(): void {
        this.handleSearchDataLoad();

        this._historyUnlistenCallback = this.props.history.listen(
            this.handleHistoryChange
        );
    }

    componentDidUpdate(): void {
        this.handleSearchDataLoad();
    }

    componentWillUnmount(): void {
        if (this._historyUnlistenCallback !== null) {
            this._historyUnlistenCallback();
        }
    }

    bindEventHandlers(): void {
        this.handleHistoryChange = this.handleHistoryChange.bind(this);
    }

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

    handleHistoryChange(): void {
        this.clearSearchError();
    }

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

    getTotalSearchResultCount(): number | null {
        if (
            this.state.searchResultPage === null
            || this.state.showLoadingNewQuery
        ) {
            return null;
        }
        return this.state.searchResultPage.totalResults;
    }

    getRenderSearchResultPage(): SearchResultPage | null {
        if (this.state.showLoadingNewPage) {
            return null;
        }
        return this.state.searchResultPage;
    }

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
                    loadedSearch={this.state.loadedSearch}
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
