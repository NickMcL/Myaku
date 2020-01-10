/**
 * SearchResultPageHeader component module. See [[SearchResultPageHeader]].
 */

import React from 'react';
import { Search } from 'ts/types/types';
import Tile from 'ts/components/generic/Tile';

/** Props for the [[SearchResultPageHeader]] component. */
interface SearchResultPageHeaderProps {
    /** Search whose data to dispaly in the header. */
    search: Search | null;

    /** Total result count for the search. */
    totalResults: number | null;
}
type Props = SearchResultPageHeaderProps;

/**
 * Max page number to display in the header tile.
 *
 * If the page number for the search prop is greater than this number, this
 * number will be displayed in the header instead.
 */
export const MAX_DISPLAY_PAGE_NUM = 99;


/**
 * Get the query portion of the header.
 *
 * @param search - Search whose results are currently displaying.
 *
 * @returns If the given search is non-null, returns a text element containing
 * its query.
 * If the given search is null, returns a loading inline-block element.
 */

/**
 * Get the total results element portion of the header.
 *
 * @param search - Search whose results are currently displaying.
 * @param totalResults - Total result count for the search.
 *
 * @returns If the given total results is non-null, returns an element
 * containing the given total results number.
 * If the given total results is null, returns a loading inline-block element.
 */
function getTotalResultsElement(
    search: Search | null, totalResults: number | null
): React.ReactNode {
    if (search === null || totalResults === null) {
        var style: React.CSSProperties = {
            width: '5em',
            height: '1em',
            display: 'inline-block',
        };
        return <div className='loading' style={style}></div>;
    }

    var queryElements: React.ReactNode[] = [];
    if (totalResults === 0) {
        queryElements.push(' for ');
        queryElements.push(<span key='query' lang='ja'>{search.query}</span>);
    }

    return (
        <small>
            {`— ${totalResults.toLocaleString('en-US')} found`}
            {queryElements}
        </small>
    );
}

/**
 * Get the page number element portion of the header.
 *
 * @param search - Search whose results are currently displaying.
 * @param totalResults - Total result count for the search.
 *
 * @returns If search is non-null and totalResult is greater than 0, returns a
 * text element containing the given page number.
 * If search is null or totalResults is not greater than 0, returns null.
 */
function getPageNumElement(
    search: Search | null, totalResults: number | null
): React.ReactNode {
    if (search === null || totalResults === null || totalResults === 0) {
        return null;
    }

    var pageNum = search.pageNum;
    if (pageNum > MAX_DISPLAY_PAGE_NUM) {
        pageNum = MAX_DISPLAY_PAGE_NUM;
    }

    var classList = ['result-header-page-number'];
    return (
        <small className={classList.join(' ')}>
            {`Page ${pageNum.toLocaleString('en-US')}`}
        </small>
    );
}

/**
 * Header component for a page of search results
 *
 * @param props - See [[SearchResultPageHeaderProps]].
 */
const SearchResultPageHeader: React.FC<Props> = function(props) {
    return (
        <Tile tileClasses='results-header-tile'>
            <h3>
                <span>
                    {'Articles '}
                    {getTotalResultsElement(props.search, props.totalResults)}
                </span>
                {getPageNumElement(props.search, props.totalResults)}
            </h3>
        </Tile>
    );
};

export default SearchResultPageHeader;
