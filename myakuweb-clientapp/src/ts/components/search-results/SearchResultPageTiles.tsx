/** @module Search result component that displays as tiles */

import React from 'react';
import SearchResultPageHeader from
    'ts/components/search-results/SearchResultPageHeader';
import SearchResultPageNav from
    'ts/components/search-results/SearchResultPageNav';
import SearchResultTile from
    'ts/components/search-results/SearchResultTile';

import {
    PageDirection,
    Search,
    SearchResultPage,
} from 'ts/types/types';

interface SearchResultPageTilesProps {
    search: Search | null;
    resultPage: SearchResultPage | null;
    loadingPageNum: number | null;
}
type Props = SearchResultPageTilesProps;

const LOADING_TILE_COUNT = 10;
const MAX_DISPLAY_PAGE_NUM = 99;


function getHeaderPageNum(props: Props): number | null {
    if (props.search === null) {
        return null;
    }

    if (props.search.pageNum > MAX_DISPLAY_PAGE_NUM) {
        return MAX_DISPLAY_PAGE_NUM;
    }
    return props.search.pageNum;
}

function getSearchResultTiles(props: Props): React.ReactElement[] {
    var tiles: React.ReactElement[] = [];
    if (props.resultPage === null) {
        for (let i = 0; i < LOADING_TILE_COUNT; ++i) {
            tiles.push(
                <SearchResultTile
                    key={i}
                    searchQuery={null}
                    searchResult={null}
                />
            );
        }
    } else {
        for (const result of props.resultPage.results) {
            tiles.push(
                <SearchResultTile
                    key={result.articleId}
                    searchQuery={props.resultPage.search.query}
                    searchResult={result}
                />
            );
        }
    }
    return tiles;
}

function getLoadingPageDirection(
    currentPageNum: number, loadingPageNum: number | null
): PageDirection | null {
    if (loadingPageNum === null) {
        return null;
    } else if (loadingPageNum < currentPageNum) {
        return PageDirection.Previous;
    } else if (loadingPageNum > currentPageNum) {
        return PageDirection.Next;
    } else {
        return null;
    }
}

function getPageNav(props: Props): React.ReactNode {
    if (props.resultPage === null || props.resultPage.totalResults === 0) {
        return null;
    }

    var pageNum = props.resultPage.search.pageNum;
    return (
        <SearchResultPageNav
            search={props.resultPage.search}
            hasNextPage={props.resultPage.hasNextPage}
            maxPageReached={props.resultPage.maxPageReached}
            loadingPageDirection={
                getLoadingPageDirection(pageNum, props.loadingPageNum)
            }
        />
    );
}

const SearchResultPageTiles: React.FC<Props> = function(props) {
    var totalResults = null;
    if (props.resultPage !== null) {
        totalResults = props.resultPage.totalResults;
    }

    return (
        <div className='result-tile-container'>
            <SearchResultPageHeader
                totalResults={totalResults}
                pageNum={getHeaderPageNum(props)}
            />
            {getSearchResultTiles(props)}
            {getPageNav(props)}
        </div>
    );
};

export default SearchResultPageTiles;
