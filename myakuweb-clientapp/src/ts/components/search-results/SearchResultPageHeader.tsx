/**
 * SearchResultPageHeader component module. See [[SearchResultPageHeader]].
 */

import React from 'react';
import Tile from 'ts/components/generic/Tile';

/** Props for the [[SearchResultPageHeader]] component. */
interface SearchResultPageHeaderProps {
    /** Total result count for the search */
    totalResults: number | null;

    /** Page number of the search results currently displaying */
    pageNum: number | null;
}
type Props = SearchResultPageHeaderProps;


/**
 * Get the total results element portion of the header.
 *
 * @param totalResults - Total result count for the search.
 *
 * @returns If the given total results is non-null, returns a text element
 * containing the given total results number.
 * If the given total results is null, returns a loading inline-block element.
 */
function getTotalResultsElement(
    totalResults: number | null
): React.ReactNode {
    if (totalResults === null) {
        var style: React.CSSProperties = {
            width: '5em',
            height: '1em',
            display: 'inline-block',
        };
        return <div className='loading' style={style}></div>;
    }

    return `${totalResults.toLocaleString('en-US')} found`;
}

/**
 * Get the page number element portion of the header.
 *
 * @param pageNum - Page number of the search results currently displaying.
 * @param totalResults - Total result count for the search.
 *
 * @returns If pageNum is non-null and totalResult is greater than 0, returns a
 * text element containing the given page number.
 * If pageNum is null or totalResults is not greater than 0, returns null.
 */
function getPageNumElement(
    pageNum: number | null, totalResults: number | null
): React.ReactNode {
    if (pageNum === null || totalResults === 0) {
        return null;
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
                    <small>
                        {'— '}
                        {getTotalResultsElement(props.totalResults)}
                    </small>
                </span>
                {getPageNumElement(props.pageNum, props.totalResults)}
            </h3>
        </Tile>
    );
};

export default SearchResultPageHeader;
