/**
 * SearchResultHeader component module. See [[SearchResultHeader]].
 */

import { ArticleSearchResult } from 'ts/types/types';
import React from 'react';

/** Props for the [[SearchResultHeader]] component. */
interface SearchResultHeaderProps {
    /** Article search result content that the header should be for. */
    searchResult: ArticleSearchResult;
}
type Props = SearchResultHeaderProps;


/**
 * Header component for an article search result.
 *
 * @param props - See [[SearchResultHeaderProps]].
 */
const SearchResultHeader: React.FC<Props> = function(props) {
    return (
        <h4 className='main-tile-header' lang='ja'>
            <a href={props.searchResult.sourceUrl}>
                {props.searchResult.title}
            </a>
        </h4>
    );
};

export default SearchResultHeader;
