/** @module Root component for MyakuWeb */

import Header from './Header';
import HeaderNav from './HeaderNav';
import HeaderSearchForm from './HeaderSearchForm';
import MainContent from './MainContent';
import React from 'react';
import { SearchOptions } from '../types';
import SearchResultsWithResources from './SearchResultsWithResources';
import StartContent from './StartContent';

interface MyakuWebState {
    submittedSearchQuery: string | null;
    submittedSearchPageNum: number | null;
    submittedSearchOptions: SearchOptions | null;
    searchQueryConvertedCallback?: (convertedQuery: string) => void;
}


class MyakuWeb extends React.Component<{}, MyakuWebState> {
    constructor(props: {}) {
        super(props);
        this.bindEventHandlers();
        this.state = {
            submittedSearchQuery: null,
            submittedSearchPageNum: null,
            submittedSearchOptions: null,
        };
    }

    bindEventHandlers(): void {
        this.handleSearchSubmit = this.handleSearchSubmit.bind(this);
    }

    handleSearchSubmit(
        query: string, pageNum: number, options: SearchOptions,
        queryConvertedCallback: (convertedQuery: string) => void
    ): void {
        this.setState({
            submittedSearchQuery: query,
            submittedSearchPageNum: pageNum,
            submittedSearchOptions: options,
            searchQueryConvertedCallback: queryConvertedCallback,
        });
    }

    handleSearchQueryConverted(convertedQuery: string): void {
        if (this.state.searchQueryConvertedCallback) {
            this.state.searchQueryConvertedCallback(convertedQuery);
        }
    }

    render(): React.ReactElement {
        var mainContent;
        if (this.state.submittedSearchQuery !== null) {
            mainContent = (
                <SearchResultsWithResources
                    searchQuery={this.state.submittedSearchQuery}
                    searchPageNum={this.state.submittedSearchPageNum}
                    searchOptions={this.state.submittedSearchOptions}
                    onSearchQueryConverted={this.handleSearchQueryConverted}
                />
            );
        } else {
            mainContent = <StartContent />;
        }

        return (
            <React.Fragment>
                <Header>
                    <HeaderNav />
                    <HeaderSearchForm
                        onSearchSubmit={this.handleSearchSubmit}
                    />
                </Header>
                <MainContent>{mainContent}</MainContent>
            </React.Fragment>
        );
    }
}

export default MyakuWeb;
