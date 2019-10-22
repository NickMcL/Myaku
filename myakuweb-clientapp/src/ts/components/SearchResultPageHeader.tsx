/** @module Header component for a page of search results */

import React from 'react';
import Tile from './Tile';

interface SearchResultPageHeaderProps {
    totalResults: number;
    pageNum: number | null;
}
type Props = SearchResultPageHeaderProps;


const SearchResultPageHeader: React.FC<Props> = function(props) {
    var pageNumElement: React.ReactElement | null = null;
    if (props.pageNum !== null) {
        pageNumElement = (
            <small className='result-header-page-number'>
                {`Page ${props.pageNum.toLocaleString('en-US')}`}
            </small>
        );
    }

    return (
        <Tile tileClasses='results-header-tile'>
            <h3>
                <span>
                    {'Articles '}
                    <small>
                        {'— '}
                        {props.totalResults.toLocaleString('en-US')}
                        {' found'}
                    </small>
                </span>
                {pageNumElement}
            </h3>
        </Tile>
    );
};

export default SearchResultPageHeader;
