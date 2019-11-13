/**
 * SearchResultPageNav component module. See [[SearchResultPageNav]].
 */

import { Link } from 'react-router-dom';
import React from 'react';
import { Search } from 'ts/types/types';
import Tile from 'ts/components/generic/Tile';
import { ViewportSize } from 'ts/app/viewport';
import { getSearchUrl } from 'ts/app/search';
import { scrollToTop } from 'ts/app/utils';
import useViewportReactiveValue from 'ts/hooks/useViewportReactiveValue';

/** Props for the [[SearchResultPageNav]] component. */
interface SearchResultPageNavProps {
    /** Current search whose results are being displayed. */
    search: Search;

    /**
     * Whether the current search has a next page of results available or not.
     */
    hasNextPage: boolean;

    /**
     * Whether the page number of the current search is the max allowable
     * page number or not.
     *
     * The page nav will not render a link to go to a next page if this is
     * true even if hasNextPage is true.
     */
    maxPageReached: boolean;
}
type Props = SearchResultPageNavProps;

// The rendered text in the page nav switches to a shortened version if the
// viewport size is very small in order to fit all of the text on a single
// line.
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


/**
 * Get the previous page Link element to use for the page nav.
 *
 * @param props - The props given to the SearchResultPageNav component.
 *
 * @returns If the search prop has a page number greater than 1, a Link element
 * to the previous page of search results. Otherwise, null.
 */
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
    return (
        <Link key='previous' to={prevPageLink}>
            <i className='fa fa-arrow-left'></i>
            {` ${prevPageLinkText}`}
        </Link>
    );
}

/**
 * Get a max page reached notice element to use for the page nav.
 */
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

/**
 * Get an end of results reached notice element to use for the page nav.
 */
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

/**
 * Get the next page Link element to use for the page nav.
 *
 * @param props - The props given to the SearchResultPageNav component.
 *
 * @returns
 * If the maxPageReached prop is true, a max page reached notice element.
 * If the maxPageReached prop is false and the hasNextPage prop is false, an
 * end of results notice element.
 * In all other cases, a Link element to the next page of search results.
 */
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
    return (
        <Link key='next' to={nextPageLink}>
            {`${nextPageLinkText} `}
            <i className='fa fa-arrow-right'></i>
        </Link>
    );
}

/**
 * Get a button that scrolls to the top of the page on click.
 */
function getGoToTopButton(): React.ReactElement {
    return (
        <button
            className='button-link page-nav-button'
            key='top'
            type='button'
            onClick={scrollToTop}
        >
            Top
        </button>
    );
}

/**
 * Page navigation component for a search result page.
 *
 * @param props - See [[SearchResultPageNavProps]].
 */
const SearchResultPageNav: React.FC<Props> = function(props) {
    return (
        <Tile tileClasses='page-nav-tile'>
            {usePreviousPageLink(props)}
            {getGoToTopButton()}
            {useNextPageLink(props)}
        </Tile>
    );
};

export default SearchResultPageNav;
