/** @module Search result component that displays as tiles */

import React from 'react';
import SearchResultPageHeader from './SearchResultPageHeader';
import SearchResultPageNav from './SearchResultPageNav';
import SearchResultTile from './SearchResultTile';

import {
    PageDirection,
    SearchResultPage,
} from '../types';

interface SearchResultPageTilesProps {
    resultPage: SearchResultPage;
    loadingPageNum: number | null;
    onPageChange: (newPageNum: number) => void;
}
type Props = SearchResultPageTilesProps;


function getHeaderPageNum(props: Props): number | null {
    if (
        props.resultPage.search.pageNum === 1
        && !props.resultPage.hasNextPage
    ) {
        return null;
    }
    return props.resultPage.search.pageNum;
}

function getSearchResultTiles(props: Props): React.ReactElement[] {
    var tiles: React.ReactElement[] = [];
    for (const result of props.resultPage.results) {
        tiles.push(
            <SearchResultTile
                key={result.articleId}
                searchQuery={props.resultPage.search.query}
                searchResult={result}
            />
        );
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
    if (props.resultPage.totalResults === 0) {
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
            onPageChange={props.onPageChange}
        />
    );
}

const SearchResultPageTiles: React.FC<Props> = function(props) {
    return (
        <div className='result-tile-container'>
            <SearchResultPageHeader
                totalResults={props.resultPage.totalResults}
                pageNum={getHeaderPageNum(props)}
            />
            {getSearchResultTiles(props)}
            {getPageNav(props)}
        </div>
    );
};

export default SearchResultPageTiles;
