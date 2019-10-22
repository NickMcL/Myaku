/** @module Root component for MyakuWeb */

import Header from './Header';
import HeaderNav from './HeaderNav';
import HeaderSearchForm from './HeaderSearchForm';
import MainContent from './MainContent';
import React from 'react';
import SearchResourceTiles from './SearchResourceTiles';
import SearchResultPageCache from '../SearchResultPageCache';
import SearchResultPageTiles from './SearchResultPageTiles';
import StartContent from './StartContent';
import { getSearchUrl } from '../utils';

import {
    Search,
    SearchResources,
    SearchResultPage,
} from '../types';
import {
    getSearchResultPage,
    getSearchWithResources,
} from '../apiRequests';

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


function getDocumentTitle(state: State): string {
    var title = 'Myaku';
    if (state.requestedSearch !== null) {
        const query = state.requestedSearch.query;
        const pageNum = state.requestedSearch.pageNum;
        title = `${query} - Page ${pageNum} - Myaku`;
    }
    return title;
}

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

function pushWindowState(state: State, replace = false): void {
    var title = getDocumentTitle(state);
    var url = '/';
    if (state.requestedSearch !== null) {
        url = getSearchUrl(state.requestedSearch);
    }

    document.title = title;
    if (replace) {
        window.history.replaceState(state, title, url);
    } else {
        window.history.pushState(state, title, url);
    }
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
        pushWindowState(this.state, true);
        window.addEventListener('popstate', this.handleWindowPopState);
    }

    componentWillUnmount(): void {
        window.removeEventListener('popstate', this.handleWindowPopState);
    }

    bindEventHandlers(): void {
        this.handleWindowPopState = this.handleWindowPopState.bind(this);
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
        this.handlePageChanged = this.handlePageChanged.bind(this);
    }

    handleWindowPopState(event: PopStateEvent): void {
        function updateState(): State {
            document.title = getDocumentTitle(event.state);
            return event.state as State;
        }

        if (event.state !== null) {
            this.setState(updateState);
        }
    }

    handleInputtedSearchQueryChange(newValue: string): void {
        this.setState({
            inputtedSearchQuery: newValue,
        });
    }

    handleSearchPageChange(newPageNum: number): void {
        function updateState(
            this: MyakuWeb, prevState: State
        ): (
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

            var search: Search = {
                ...prevState.requestedSearch,
                pageNum: newPageNum,
            };
            var cachedPage = this._visitedPageCache.get(search);
            if (cachedPage !== null) {
                return {
                    requestedSearch: search,
                    requestedSearchType: SearchType.NewPage,
                    searchResultPage: cachedPage,
                    fetchingSearchResults: false,
                };
            }

            getSearchResultPage(search).then(this.handleSearchResponse);
            return {
                requestedSearch: search,
                requestedSearchType: SearchType.NewPage,
                fetchingSearchResults: true,
            };
        }

        this.setState(updateState.bind(this), this.handlePageChanged);
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
            return {
                requestedSearch: search,
                requestedSearchType: SearchType.NewQuery,
                fetchingSearchResults: true,
            };
        }

        this.setState(updateState.bind(this));
    }

    handleReturnToStart(): void {
        this.setState(getStartState(), this.handlePageChanged);
    }

    handleSearchResponse(response: SearchResultPage): void {
        function updateState(prevState: State): Pick<
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

        this.setState(updateState, this.handlePageChanged);
    }

    handleSearchWithResourcesResponse(
        response: [SearchResultPage, SearchResources]
    ): void {
        function updateState(prevState: State): Pick<
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

        this.setState(updateState, this.handlePageChanged);
    }

    handlePageChanged(): void {
        if (this.state.fetchingSearchResults) {
            return;
        }

        window.scrollTo(0, 0);
        pushWindowState(this.state);
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
