/**
 * Queried search results display component.
 * @module ts/components/search-results/SearchResults
 */

import ContentLoader from 'ts/components/generic/ContentLoader';
import History from 'history';
import React from 'react';
import SearchResourceTiles from
    'ts/components/search-results/SearchResourceTiles';
import SearchResultPageTiles from
    'ts/components/search-results/SearchResultPageTiles';
import StartContent from 'ts/components/start/StartContent';

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
    requestedSearch: Search | null;
    requestedSearchType: SearchType | null;
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


function getDocumentTitle(search: Search): string {
    return `${search.query} - Page ${search.pageNum} - Myaku`;
}

class SearchResults extends React.Component<Props, State> {
    constructor(props: Props) {
        super(props);
        this.state = {
            fetchingSearchResults: false,
            requestedSearch: null,
            requestedSearchType: null,
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
                props.onLoadingNewSearchQueryChange(true);
                getSearchWithResources(search).then(
                    this.getSearchWithResourcesResponseHandler(search)
                );
            }

            props.onSearchQueryChange(search.query);
            return {
                requestedSearch: search,
                requestedSearchType: searchType,
                fetchingSearchResults: true,
            };
        }

        this.setState(updateState.bind(this));
    }

    handleSearchResultsLoaded(): void {
        window.scrollTo(0, 0);
    }

    getSearchResponseHandler(
        search: Search
    ): (response: SearchResultPage) => void {
        function handler(
            this: SearchResults, response: SearchResultPage
        ): void {
            function updateState(prevState: State, props: Props): (
                Pick<State, 'searchResultPage' | 'fetchingSearchResults'>
                | null
            ) {
                if (!isSearchEqual(search, prevState.requestedSearch)) {
                    return null;
                }

                document.title = getDocumentTitle(response.search);
                props.onSearchQueryChange(response.search.query);
                props.onLoadingNewSearchQueryChange(false);
                return {
                    searchResultPage: response,
                    fetchingSearchResults: false,
                };
            }

            this.setState(updateState, this.handleSearchResultsLoaded);
        }

        return handler.bind(this);
    }

    getSearchWithResourcesResponseHandler(
        search: Search
    ): (response: [SearchResultPage, SearchResources]) => void {
        function handler(
            this: SearchResults, response: [SearchResultPage, SearchResources]
        ): void {
            function updateState(prevState: State, props: Props): (
                Pick<
                    State,
                    'searchResultPage'
                    | 'searchResources'
                    | 'fetchingSearchResults'
                >
                | null
            ) {
                if (!isSearchEqual(search, prevState.requestedSearch)) {
                    return null;
                }

                document.title = getDocumentTitle(response[0].search);
                props.onSearchQueryChange(response[0].search.query);
                props.onLoadingNewSearchQueryChange(false);
                return {
                    searchResultPage: response[0],
                    searchResources: response[1],
                    fetchingSearchResults: false,
                };
            }

            this.setState(updateState, this.handleSearchResultsLoaded);
        }

        return handler.bind(this);
    }

    getLoadingPageNum(): number | null {
        if (
            this.state.fetchingSearchResults
            && this.state.requestedSearch !== null
            && this.state.requestedSearchType === SearchType.NewPage
        ) {
            return this.state.requestedSearch.pageNum;
        } else {
            return null;
        }
    }

    getSearchResultsContent(): React.ReactNode {
        if (
            this.state.searchResultPage === null
            || this.state.searchResources === null
        ) {
            return null;
        }

        return (
            <React.Fragment>
                <SearchResultPageTiles
                    resultPage={this.state.searchResultPage}
                    loadingPageNum={this.getLoadingPageNum()}
                />
                <SearchResourceTiles resources={this.state.searchResources} />
            </React.Fragment>
        );
    }

    render(): React.ReactNode {
        if (
            this.state.searchResultPage !== null
            && this.state.searchResources !== null
        ) {
            return this.getSearchResultsContent();
        } else if (this.props.history.length === 1) {
            return <ContentLoader />;
        } else {
            return <StartContent />;
        }
    }
}

export default SearchResults;
