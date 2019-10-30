/** @module Header component for a page of search results */

import React from 'react';
import Tile from 'ts/components/generic/Tile';

interface SearchResultPageHeaderProps {
    totalResults: number | null;
    pageNum: number | null;
}
type Props = SearchResultPageHeaderProps;


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
