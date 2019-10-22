/** @module Header component for an article search result */

import { ArticleSearchResult } from '../types';
import React from 'react';

interface SearchResultHeaderProps {
    searchResult: ArticleSearchResult;
}
type Props = SearchResultHeaderProps;


const SearchResultHeader: React.FC<Props> = function(props) {
    return (
        <h4 className='main-tile-header japanese-text' lang='ja'>
            <a href={props.searchResult.sourceUrl}>
                {props.searchResult.title}
            </a>
        </h4>
    );
};

export default SearchResultHeader;
