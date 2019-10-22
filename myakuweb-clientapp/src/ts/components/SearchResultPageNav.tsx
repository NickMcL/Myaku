/** @module Page navigation component for a search result page */

import React from 'react';
import Tile from './Tile';
import { getSearchUrl } from '../utils';

import {
    PageDirection,
    Search,
} from '../types';

interface SearchResultPageNavProps {
    search: Search;
    hasNextPage: boolean;
    maxPageReached: boolean;
    loadingPageDirection: PageDirection | null;
    onPageChange: (newPageNum: number) => void;
}
type Props = SearchResultPageNavProps;


function getPageNavClickHandler(
    newPageNum: number, onPageChange: (newPageNum: number) => void
): (event: React.SyntheticEvent) => void {
    return function(event: React.SyntheticEvent): void {
        event.preventDefault();
        onPageChange(newPageNum);
    };
}

function getPreviousPageLinks(props: Props): React.ReactElement[] | null {
    var prevPageNum = props.search.pageNum - 1;
    if (prevPageNum < 1) {
        return null;
    }

    var prevPageLink = getSearchUrl({
        ...props.search,
        pageNum: prevPageNum,
    });
    var handlePrevPageNav = getPageNavClickHandler(
        prevPageNum, props.onPageChange
    );
    return [
        <a
            key='prev-long'
            className='page-nav-long'
            href={prevPageLink}
            onClick={handlePrevPageNav}
        >
            <i className='fa fa-arrow-left'></i>
            {' Previous Articles'}
        </a>,
        <a
            key='prev-short'
            className='page-nav-short'
            href={prevPageLink}
            onClick={handlePrevPageNav}
        >
            <i className='fa fa-arrow-left'></i>
            {' Previous'}
        </a>,
    ];
}

function getMaxPageReachedNotices(): React.ReactElement[] {
    return [
        <span key='max-long' className='page-info-long'>
            Max page reached
        </span>,
        <span key='max-short' className='page-info-short'>
            Max page
        </span>,
    ];
}

function getEndOfResultsNotices(pageNum: number): React.ReactElement[] {
    var shortText = 'End';
    if (pageNum === 1) {
        shortText = 'End of results';
    }

    return [
        <span key='end-long' className='page-info-long'>
            End of results
        </span>,
        <span key='end-short' className='page-info-short'>
            {shortText}
        </span>,
    ];
}

function getNextPageLinks(props: Props): React.ReactElement[] {
    if (props.maxPageReached) {
        return getMaxPageReachedNotices();
    }
    if (!props.hasNextPage) {
        return getEndOfResultsNotices(props.search.pageNum);
    }

    var nextPageNum = props.search.pageNum + 1;
    var nextPageLink = getSearchUrl({
        ...props.search,
        pageNum: nextPageNum,
    });
    var handleNextPageNav = getPageNavClickHandler(
        nextPageNum, props.onPageChange
    );
    return [
        <a
            key='next-long'
            className='page-nav-long'
            href={nextPageLink}
            onClick={handleNextPageNav}
        >
            {'More Articles '}
            <i className='fa fa-arrow-right'></i>
        </a>,
        <a
            key='next-short'
            className='page-nav-short'
            href={nextPageLink}
            onClick={handleNextPageNav}
        >
            {'More '}
            <i className='fa fa-arrow-right'></i>
        </a>,
    ];
}

const SearchResultPageNav: React.FC<Props> = function(props) {
    return (
        <Tile tileClasses='page-nav-tile'>
            {getPreviousPageLinks(props)}
            <a key='top' href='#top'>Top</a>
            {getNextPageLinks(props)}
        </Tile>
    );
};

export default SearchResultPageNav;
