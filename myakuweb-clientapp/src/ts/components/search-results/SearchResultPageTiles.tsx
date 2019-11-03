/** @module Search result component that displays as tiles */

import React from 'react';
import SearchResultPageHeader from
    'ts/components/search-results/SearchResultPageHeader';
import SearchResultPageNav from
    'ts/components/search-results/SearchResultPageNav';
import SearchResultTile from
    'ts/components/search-results/SearchResultTile';

import {
    Search,
    SearchResultPage,
} from 'ts/types/types';

interface SearchResultPageTilesProps {
    requestedSearch: Search | null;
    loadedSearch: Search | null;
    totalResults: number | null;
    resultPage: SearchResultPage | null;
}
type Props = SearchResultPageTilesProps;

const LOADING_TILE_COUNT = 10;
const MAX_DISPLAY_PAGE_NUM = 99;


function getHeaderPageNum(props: Props): number | null {
    if (props.requestedSearch === null) {
        return null;
    }

    if (props.requestedSearch.pageNum > MAX_DISPLAY_PAGE_NUM) {
        return MAX_DISPLAY_PAGE_NUM;
    }
    return props.requestedSearch.pageNum;
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

function getPageNav(props: Props): React.ReactNode {
    if (
        props.loadedSearch === null
        || props.resultPage === null
        || props.resultPage.totalResults === 0
    ) {
        return null;
    }

    return (
        <SearchResultPageNav
            search={props.loadedSearch}
            hasNextPage={props.resultPage.hasNextPage}
            maxPageReached={props.resultPage.maxPageReached}
        />
    );
}

const SearchResultPageTiles: React.FC<Props> = function(props) {
    return (
        <div className='result-tile-container'>
            <SearchResultPageHeader
                totalResults={props.totalResults}
                pageNum={getHeaderPageNum(props)}
            />
            {getSearchResultTiles(props)}
            {getPageNav(props)}
        </div>
    );
};

export default SearchResultPageTiles;
