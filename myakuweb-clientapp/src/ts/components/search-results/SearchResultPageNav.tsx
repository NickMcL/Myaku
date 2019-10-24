/**
 * Page navigation component for a search result page.
 * @module ts/components/search-results/SearchResultPageNav
 */

import React from 'react';
import Tile from 'ts/components/generic/Tile';
import { ViewportSize } from 'ts/app/viewport';
import { getSearchUrl } from 'ts/app/utils';
import useViewportReactiveValue from 'ts/hooks/useViewportReactiveValue';

import {
    PageDirection,
    Search,
} from 'ts/types/types';

interface SearchResultPageNavProps {
    search: Search;
    hasNextPage: boolean;
    maxPageReached: boolean;
    loadingPageDirection: PageDirection | null;
    onPageChange: (newPageNum: number) => void;
}
type Props = SearchResultPageNavProps;

const SHORT_PREVIOUS_TEXT = 'Previous';
const LONG_PREVIOUS_TEXT = 'Previous articles';
const DEFAULT_PREVIOUS_TEXT = SHORT_PREVIOUS_TEXT;
const VIEWPORT_PREVIOUS_TEXT = {
    [ViewportSize.Small]: LONG_PREVIOUS_TEXT,
};

const SHORT_NEXT_TEXT = 'More';
const LONG_NEXT_TEXT = 'More articles';
const DEFAULT_NEXT_TEXT = SHORT_NEXT_TEXT;
const VIEWPORT_NEXT_TEXT = {
    [ViewportSize.Small]: LONG_NEXT_TEXT,
};

const SHORT_END_TEXT = 'End';
const LONG_END_TEXT = 'End of results';
const DEFAULT_END_TEXT = SHORT_END_TEXT;
const VIEWPORT_END_TEXT = {
    [ViewportSize.Small]: LONG_END_TEXT,
};

const SHORT_MAX_PAGE_TEXT = 'Max page';
const LONG_MAX_PAGE_TEXT = 'Max page reached';
const DEFAULT_MAX_PAGE_TEXT = SHORT_MAX_PAGE_TEXT;
const VIEWPORT_MAX_PAGE_TEXT = {
    [ViewportSize.Small]: LONG_MAX_PAGE_TEXT,
};


function getPageNavClickHandler(
    newPageNum: number, onPageChange: (newPageNum: number) => void
): (event: React.SyntheticEvent) => void {
    return function(event: React.SyntheticEvent): void {
        event.preventDefault();
        onPageChange(newPageNum);
    };
}

function usePreviousPageLink(props: Props): React.ReactElement | null {
    const prevPageLinkText = useViewportReactiveValue(
        DEFAULT_PREVIOUS_TEXT, VIEWPORT_PREVIOUS_TEXT
    );
    const prevPageNum = props.search.pageNum - 1;
    if (prevPageNum < 1) {
        return null;
    }

    const prevPageLink = getSearchUrl({
        ...props.search,
        pageNum: prevPageNum,
    });
    const handlePrevPageNav = getPageNavClickHandler(
        prevPageNum, props.onPageChange
    );
    return (
        <a key='previous' href={prevPageLink} onClick={handlePrevPageNav}>
            <i className='fa fa-arrow-left'></i>
            {` ${prevPageLinkText}`}
        </a>
    );
}

function useMaxPageReachedNotice(): React.ReactElement {
    const maxPageText = useViewportReactiveValue(
        DEFAULT_MAX_PAGE_TEXT, VIEWPORT_MAX_PAGE_TEXT
    );
    return (
        <span key='max-page' className='page-info'>
            {maxPageText}
        </span>
    );
}

function useEndOfResultsNotice(pageNum: number): React.ReactElement {
    var endText = useViewportReactiveValue(
        DEFAULT_END_TEXT, VIEWPORT_END_TEXT
    );
    if (pageNum === 1) {
        // Always use the long text version on page 1 since there's more space
        // available in that case since the previous page link won't be there.
        endText = LONG_END_TEXT;
    }
    return (
        <span key='end' className='page-info'>
            {endText}
        </span>
    );
}

function useNextPageLink(props: Props): React.ReactElement {
    const nextPageLinkText = useViewportReactiveValue(
        DEFAULT_NEXT_TEXT, VIEWPORT_NEXT_TEXT
    );
    const maxPageElement = useMaxPageReachedNotice();
    const endOfResultsElement = useEndOfResultsNotice(props.search.pageNum);
    if (props.maxPageReached) {
        return maxPageElement;
    }
    if (!props.hasNextPage) {
        return endOfResultsElement;
    }

    const nextPageNum = props.search.pageNum + 1;
    const nextPageLink = getSearchUrl({
        ...props.search,
        pageNum: nextPageNum,
    });
    const handleNextPageNav = getPageNavClickHandler(
        nextPageNum, props.onPageChange
    );
    return (
        <a key='next' href={nextPageLink} onClick={handleNextPageNav}>
            {`${nextPageLinkText} `}
            <i className='fa fa-arrow-right'></i>
        </a>
    );
}

const SearchResultPageNav: React.FC<Props> = function(props) {
    return (
        <Tile tileClasses='page-nav-tile'>
            {usePreviousPageLink(props)}
            <a key='top' href='#top'>Top</a>
            {useNextPageLink(props)}
        </Tile>
    );
};

export default SearchResultPageNav;
