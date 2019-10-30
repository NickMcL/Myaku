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
    fetchingSearchResults: boolean;
    showLoadingIndicator: boolean;
    requestedSearch: Search | null;
    requestedSearchType: SearchType | null;
    loadedSearch: Search | null;
    searchResultPage: SearchResultPage | null;
    searchResources: SearchResources | null;
}
type State = SearchResultsState;

type RequestedSearchState = (
    Pick<
        State,
        'fetchingSearchResults'
        | 'requestedSearch'
        | 'requestedSearchType'
    >
);

type SearchResponseState = (
    Pick<
        State,
        'searchResultPage'
        | 'loadedSearch'
        | 'fetchingSearchResults'
        | 'showLoadingIndicator'
    >
    | Pick<
        State,
        'searchResultPage'
        | 'searchResources'
        | 'loadedSearch'
        | 'fetchingSearchResults'
        | 'showLoadingIndicator'
    >
);

type SearchResponse = SearchResultPage | [SearchResultPage, SearchResources];

const SHOW_LOADING_TIMEOUT = 100;


function getDocumentTitle(search: Search): string {
    return `${search.query} - Page ${search.pageNum} - Myaku`;
}

class SearchResults extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            fetchingSearchResults: false,
            showLoadingIndicator: false,
            requestedSearch: null,
            requestedSearchType: null,
            loadedSearch: null,
            searchResultPage: null,
            searchResources: null,
        };
    }

    componentDidMount(): void {
        this.handleLocationChange();
    }

    componentDidUpdate(): void {
        this.handleLocationChange();
    }

    handleLocationChange(): void {
        var search = getSearchFromLocation(this.props.location);
        if (search.query.length === 0) {
            // Redirect to start page because search is invalid (no query)
            this.props.history.replace('/');
        } else if (!isSearchEqual(search, this.state.requestedSearch)) {
            this.handleSearchRequest(search);
        }
    }

    handleSearchRequest(search: Search): void {
        function updateState(
            this: SearchResults, prevState: State, props: Props
        ): RequestedSearchState {
            var searchType: SearchType;
            if (
                prevState.requestedSearch !== null
                && search.query === prevState.requestedSearch.query
            ) {
                searchType = SearchType.NewPage;
                getSearchResultPage(search).then(
                    this.getSearchResponseHandler(search)
                );
            } else {
                searchType = SearchType.NewQuery;
                getSearchWithResources(search).then(
                    this.getSearchResponseHandler(search)
                );
            }

            props.onSearchQueryChange(search.query);
            setTimeout(
                this.getShowLoadingIndicatorHandler(search),
                SHOW_LOADING_TIMEOUT
            );
            return {
                requestedSearch: search,
                requestedSearchType: searchType,
                fetchingSearchResults: true,
            };
        }

        this.setState(updateState.bind(this));
    }

    getShowLoadingIndicatorHandler(search: Search): () => void {
        function handler(this: SearchResults): void {
            function updateState(prevState: State, props: Props): (
                Pick<State, 'showLoadingIndicator'> | null
            ) {
                if (isSearchEqual(search, prevState.loadedSearch)) {
                    return null;
                }

                if (
                    prevState.loadedSearch === null
                    || search.query !== prevState.loadedSearch.query
                ) {
                    props.onLoadingNewSearchQueryChange(true);
                }
                return {
                    showLoadingIndicator: true,
                };
            }

            this.setState(updateState);
        }

        return handler.bind(this);
    }

    handleSearchResultsLoaded(): void {
        window.scrollTo(0, 0);
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
                    searchResultPage: searchResultPage,
                    searchResources: searchResources,
                    loadedSearch: search,
                    fetchingSearchResults: false,
                    showLoadingIndicator: false,
                };
            }

            this.setState(updateState, this.handleSearchResultsLoaded);
        }

        return handler.bind(this);
    }

    getLoadingPageNum(): number | null {
        if (
            this.state.showLoadingIndicator
            && this.state.requestedSearch !== null
            && this.state.requestedSearchType === SearchType.NewPage
        ) {
            return this.state.requestedSearch.pageNum;
        } else {
            return null;
        }
    }

    render(): React.ReactElement {
        return (
            <React.Fragment>
                <SearchResultPageTiles
                    search={this.state.requestedSearch}
                    resultPage={this.state.searchResultPage}
                    loadingPageNum={this.getLoadingPageNum()}
                />
                <SearchResourceTiles resources={this.state.searchResources} />
            </React.Fragment>
        );
    }
}

export default SearchResults;
