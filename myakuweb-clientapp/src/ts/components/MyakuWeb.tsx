/** @module Root component for MyakuWeb */

import Header from 'ts/components/header/Header';
import HeaderNav from 'ts/components/header/HeaderNav';
import HeaderSearchForm from 'ts/components/header/HeaderSearchForm';
import HistoryStateSaver from 'ts/components/generic/HistoryStateSaver';
import MainContent from 'ts/components/generic/MainContent';
import { PAGE_NAVIGATION_EVENT } from 'ts/app/events';
import React from 'react';
import SearchResourceTiles from
    'ts/components/search-results/SearchResourceTiles';
import SearchResultPageCache from 'ts/app/SearchResultPageCache';
import SearchResultPageTiles from
    'ts/components/search-results/SearchResultPageTiles';
import StartContent from 'ts/components/start-page/StartContent';
import { getSearchUrl } from 'ts/app/utils';

import {
    Search,
    SearchResources,
    SearchResultPage,
} from 'ts/types/types';
import {
    getSearchResultPage,
    getSearchWithResources,
} from 'ts/app/apiRequests';

const enum SearchType {
    NewQuery = 'query',
    NewPage = 'page',
}

interface MyakuWebState {
    inputtedSearchQuery: string;
    fetchingSearchResults: boolean;
    requestedSearch: Search | null;
    requestedSearchType: SearchType | null;
    searchResultPage: SearchResultPage | null;
    searchResources: SearchResources | null;
}
type State = MyakuWebState;

type RequestedSearchState = Pick<
    MyakuWebState,
    'fetchingSearchResults'
    | 'requestedSearch'
    | 'requestedSearchType'
>;

const SEARCH_QUERY_URL_PARAM = 'q';


function getStartState(): State {
    return {
        inputtedSearchQuery: '',
        fetchingSearchResults: false,
        requestedSearch: null,
        requestedSearchType: null,
        searchResultPage: null,
        searchResources: null,
    };
}

function getDocumentTitle(state: State): string {
    if (state.requestedSearch === null) {
        return 'Myaku';
    } else {
        const query = state.requestedSearch.query;
        const pageNum = state.requestedSearch.pageNum;
        return `${query} - Page ${pageNum} - Myaku`;
    }
}

function pushWindowState(state: State): void {
    var url = '/';
    if (state.requestedSearch !== null) {
        url = getSearchUrl(state.requestedSearch);
    }
    window.history.pushState(null, getDocumentTitle(state), url);
    window.dispatchEvent(new Event(PAGE_NAVIGATION_EVENT));
}

class MyakuWeb extends React.Component<{}, State> {
    private _visitedPageCache: SearchResultPageCache;

    constructor(props: {}) {
        super(props);
        this.bindEventHandlers();

        var urlParams = new URLSearchParams(window.location.search);
        this.state = {
            ...getStartState(),
            inputtedSearchQuery: urlParams.get(SEARCH_QUERY_URL_PARAM) || '',
        };
        this._visitedPageCache = new SearchResultPageCache();
    }

    componentDidMount(): void {
        document.title = getDocumentTitle(this.state);
        window.history.scrollRestoration = 'manual';
    }

    componentDidUpdate(): void {
        document.title = getDocumentTitle(this.state);
    }

    bindEventHandlers(): void {
        this.handleRestoreStateFromHistory = (
            this.handleRestoreStateFromHistory.bind(this)
        );
        this.handleInputtedSearchQueryChange = (
            this.handleInputtedSearchQueryChange.bind(this)
        );
        this.handleSearchPageChange = this.handleSearchPageChange.bind(this);
        this.handleSearchSubmit = this.handleSearchSubmit.bind(this);
        this.handleReturnToStart = this.handleReturnToStart.bind(this);
        this.handleSearchResponse = this.handleSearchResponse.bind(this);
        this.handleSearchWithResourcesResponse = (
            this.handleSearchWithResourcesResponse.bind(this)
        );
        this.handlePageChange = this.handlePageChange.bind(this);
        this.handleSearchResultPageLoaded = (
            this.handleSearchResultPageLoaded.bind(this)
        );
    }

    handleRestoreStateFromHistory(restoreState: State): void {
        window.scrollTo(0, 0);
        this.setState(restoreState);
    }

    handleInputtedSearchQueryChange(newValue: string): void {
        this.setState({
            inputtedSearchQuery: newValue,
        });
    }

    handleSearchPageChange(newPageNum: number): void {
        function updateState(this: MyakuWeb, prevState: State): (
            RequestedSearchState
            | RequestedSearchState & {searchResultPage: SearchResultPage}
            | null
        ) {
            if (
                prevState.fetchingSearchResults
                || prevState.requestedSearch === null
            ) {
                return null;
            }

            var updatedState;
            var search: Search = {
                ...prevState.requestedSearch,
                pageNum: newPageNum,
            };
            var cachedPage = this._visitedPageCache.get(search);
            if (cachedPage !== null) {
                updatedState = {
                    requestedSearch: search,
                    requestedSearchType: SearchType.NewPage,
                    searchResultPage: cachedPage,
                    fetchingSearchResults: false,
                };
            } else {
                getSearchResultPage(search).then(this.handleSearchResponse);
                updatedState = {
                    requestedSearch: search,
                    requestedSearchType: SearchType.NewPage,
                    fetchingSearchResults: true,
                };
            }
            pushWindowState({...prevState, ...updatedState});
            return updatedState;
        }

        this.setState(
            updateState.bind(this), this.handleSearchResultPageLoaded
        );
    }

    handleSearchSubmit(search: Search): void {
        function updateState(
            this: MyakuWeb, prevState: State
        ): RequestedSearchState | null {
            if (prevState.fetchingSearchResults) {
                return null;
            }

            if (
                prevState.requestedSearch !== null
                && search.query === prevState.requestedSearch.query
            ) {
                getSearchResultPage(search).then(this.handleSearchResponse);
            } else {
                getSearchWithResources(search)
                    .then(this.handleSearchWithResourcesResponse);
            }

            this._visitedPageCache.clear();
            var updatedState = {
                requestedSearch: search,
                requestedSearchType: SearchType.NewQuery,
                fetchingSearchResults: true,
            };
            pushWindowState({...prevState, ...updatedState});
            return updatedState;
        }

        this.setState(updateState.bind(this));
    }

    handleReturnToStart(): void {
        function updateState(this: MyakuWeb): State {
            var startState = getStartState();
            pushWindowState(startState);
            return startState;
        }

        this.setState(updateState.bind(this));
    }

    handleSearchResponse(response: SearchResultPage): void {
        function updateState(this: MyakuWeb, prevState: State): Pick<
            State,
            'inputtedSearchQuery'
            | 'searchResultPage'
            | 'fetchingSearchResults'
        > | null {
            if (!prevState.fetchingSearchResults) {
                return null;
            }

            return {
                inputtedSearchQuery: response.search.query,
                searchResultPage: response,
                fetchingSearchResults: false,
            };
        }

        this.setState(
            updateState.bind(this), this.handleSearchResultPageLoaded
        );
    }

    handleSearchWithResourcesResponse(
        response: [SearchResultPage, SearchResources]
    ): void {
        function updateState(this: MyakuWeb, prevState: State): Pick<
            State,
            'inputtedSearchQuery'
            | 'searchResultPage'
            | 'searchResources'
            | 'fetchingSearchResults'
        > | null {
            if (!prevState.fetchingSearchResults) {
                return null;
            }

            return {
                inputtedSearchQuery: response[0].search.query,
                searchResultPage: response[0],
                searchResources: response[1],
                fetchingSearchResults: false,
            };
        }

        this.setState(
            updateState.bind(this), this.handleSearchResultPageLoaded
        );
    }

    handlePageChange(updatedState: Partial<State>): void {
        pushWindowState({...this.state, ...updatedState});
    }

    handleSearchResultPageLoaded(): void {
        if (this.state.fetchingSearchResults) {
            return;
        }

        window.scrollTo(0, 0);
        if (
            this.state.requestedSearch !== null
            && this.state.searchResultPage !== null
        ) {
            this._visitedPageCache.set(
                this.state.requestedSearch,
                this.state.searchResultPage
            );
        }
    }

    getMainContent(): React.ReactElement {
        if (
            this.state.searchResultPage === null
            || this.state.searchResources === null
        ) {
            return <StartContent onSearchSubmit={this.handleSearchSubmit} />;
        }

        var loadingPageNum: number | null = null;
        if (
            this.state.fetchingSearchResults
            && this.state.requestedSearch !== null
            && this.state.requestedSearchType === SearchType.NewPage
        ) {
            loadingPageNum = this.state.requestedSearch.pageNum;
        }

        return (
            <React.Fragment>
                <SearchResultPageTiles
                    resultPage={this.state.searchResultPage}
                    loadingPageNum={loadingPageNum}
                    onPageChange={this.handleSearchPageChange}
                />
                <SearchResourceTiles resources={this.state.searchResources} />
            </React.Fragment>
        );
    }

    render(): React.ReactElement {
        var loadingNewQuery = false;
        if (
            this.state.fetchingSearchResults
            && this.state.requestedSearchType === SearchType.NewQuery
        ) {
            loadingNewQuery = true;
        }

        return (
            <React.Fragment>
                <HistoryStateSaver
                    componentKey={'MyakuWeb'}
                    currentState={this.state}
                    onRestoreStateFromHistory={
                        this.handleRestoreStateFromHistory
                    }
                />
                <Header>
                    <HeaderNav onReturnToStart={this.handleReturnToStart} />
                    <HeaderSearchForm
                        searchQuery={this.state.inputtedSearchQuery}
                        loadingSearch={loadingNewQuery}
                        onSearchSubmit={this.handleSearchSubmit}
                        onSearchQueryChange={
                            this.handleInputtedSearchQueryChange
                        }
                    />
                </Header>
                <MainContent>{this.getMainContent()}</MainContent>
            </React.Fragment>
        );
    }
}

export default MyakuWeb;
