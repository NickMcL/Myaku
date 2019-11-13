/**
 * Tests for the [[SearchResultPageTiles]] component.
 */

import React from 'react';
import SearchResultPageHeader from
    'ts/components/search-results/SearchResultPageHeader';
import SearchResultPageNav from
    'ts/components/search-results/SearchResultPageNav';
import SearchResultPageTiles from
    'ts/components/search-results/SearchResultPageTiles';
import SearchResultTile from
    'ts/components/search-results/SearchResultTile';
import { expectComponent } from 'tests/testUtils';
import { getSearchResultPageDataClone } from 'tests/testData';

import {
    LOADING_TILE_COUNT,
    MAX_DISPLAY_PAGE_NUM,
} from 'ts/components/search-results/SearchResultPageTiles';
import {
    ShallowWrapper,
    shallow,
} from 'enzyme';

var resultPage = getSearchResultPageDataClone();
var requestedSearch = getSearchResultPageDataClone().search;
var totalResults = resultPage.totalResults;
beforeEach(function() {
    resultPage = getSearchResultPageDataClone();
    requestedSearch = getSearchResultPageDataClone().search;
    totalResults = resultPage.totalResults;
});

function expectLoadingResultTiles(wrapper: ShallowWrapper): void {
    const resultTiles = wrapper.find(SearchResultTile);
    expect(resultTiles).toHaveLength(LOADING_TILE_COUNT);

    for (let i = 0; i < resultTiles.length; ++i) {
        expect(resultTiles.at(i).props()).toStrictEqual({
            searchQuery: null,
            searchResult: null,
        });
    }
}

function expectResultTiles(wrapper: ShallowWrapper): void {
    const resultTiles = wrapper.find(SearchResultTile);
    expect(resultTiles).toHaveLength(resultPage.results.length);

    for (let i = 0; i < resultPage.results.length; ++i) {
        expect(resultTiles.at(i).props()).toStrictEqual({
            searchQuery: resultPage.search.query,
            searchResult: resultPage.results[i],
        });
    }
}


describe('<SearchResultPageTiles /> header', function() {
    it('renders with all null props', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={null}
                totalResults={null}
                resultPage={null}
            />
        );
        expectComponent(wrapper, SearchResultPageHeader, {
            totalResults: null,
            pageNum: null,
        });
    });

    it('renders with only requested search set', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={null}
                resultPage={null}
            />
        );
        expectComponent(wrapper, SearchResultPageHeader, {
            totalResults: null,
            pageNum: requestedSearch.pageNum,
        });
    });

    it('renders with requested search and total results set', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={null}
            />
        );
        expectComponent(wrapper, SearchResultPageHeader, {
            totalResults: totalResults,
            pageNum: requestedSearch.pageNum,
        });
    });

    it('renders with all props set', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={resultPage}
            />
        );
        expectComponent(wrapper, SearchResultPageHeader, {
            totalResults: totalResults,
            pageNum: resultPage.search.pageNum,
        });
    });

    it('renders max page num if less than requested page num', function() {
        requestedSearch.pageNum = MAX_DISPLAY_PAGE_NUM + 1;

        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={null}
            />
        );
        expectComponent(wrapper, SearchResultPageHeader, {
            totalResults: totalResults,
            pageNum: MAX_DISPLAY_PAGE_NUM,
        });
    });

    it(
        'renders loaded page num instead of within max requested page num',
        function() {
            requestedSearch.pageNum = MAX_DISPLAY_PAGE_NUM;
            resultPage.search.pageNum = 30;

            const wrapper = shallow(
                <SearchResultPageTiles
                    requestedSearch={requestedSearch}
                    totalResults={totalResults}
                    resultPage={resultPage}
                />
            );
            expectComponent(wrapper, SearchResultPageHeader, {
                totalResults: totalResults,
                pageNum: resultPage.search.pageNum,
            });
        }
    );

    it(
        'renders loaded page num instead of over max requested page num',
        function() {
            requestedSearch.pageNum = MAX_DISPLAY_PAGE_NUM + 1;
            resultPage.search.pageNum = 30;

            const wrapper = shallow(
                <SearchResultPageTiles
                    requestedSearch={requestedSearch}
                    totalResults={totalResults}
                    resultPage={resultPage}
                />
            );
            expectComponent(wrapper, SearchResultPageHeader, {
                totalResults: totalResults,
                pageNum: resultPage.search.pageNum,
            });
        }
    );
});

describe('<SearchResultPageTiles /> result tiles', function() {
    it('renders loading tiles if no result page', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={null}
            />
        );
        expectLoadingResultTiles(wrapper);
    });

    it('renders no tiles if no results in result page', function() {
        resultPage.results = [];
        resultPage.hasNextPage = false;
        resultPage.totalResults = 0;

        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={resultPage}
            />
        );
        expect(wrapper.find(SearchResultTile)).toHaveLength(0);
    });

    it('renders 1 tile if 1 result in result page', function() {
        resultPage.results = resultPage.results.slice(0, 1);
        resultPage.hasNextPage = false;
        resultPage.totalResults = 1;

        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={resultPage}
            />
        );
        expectResultTiles(wrapper);
    });

    it('renders many tiles if many results in result page', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={resultPage}
            />
        );
        expectResultTiles(wrapper);
    });
});

describe('<SearchResultPageTiles /> page nav', function() {
    it('does not render if no result page', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={null}
            />
        );
        expect(wrapper.find(SearchResultPageNav)).toHaveLength(0);
    });

    it('does not render if result page has 0 total results', function() {
        resultPage.results = [];
        resultPage.hasNextPage = false;
        resultPage.totalResults = 0;
        totalResults = 0;

        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={resultPage}
            />
        );
        expect(wrapper.find(SearchResultPageNav)).toHaveLength(0);
    });

    it('renders if result page has at least 1 result', function() {
        const wrapper = shallow(
            <SearchResultPageTiles
                requestedSearch={requestedSearch}
                totalResults={totalResults}
                resultPage={resultPage}
            />
        );
        expectComponent(wrapper, SearchResultPageNav, {
            search: resultPage.search,
            hasNextPage: resultPage.hasNextPage,
            maxPageReached: resultPage.maxPageReached,
        });
    });
});
