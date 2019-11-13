/**
 * SearchResultTags component module. See [[SearchResultTags]].
 */

import { ArticleSearchResult } from 'ts/types/types';
import React from 'react';

/** Props for the [[SearchResultTags]] component. */
interface SearchResultTagsProps {
    /** Search result data to display tags for in the component. */
    searchResult: ArticleSearchResult;
}
type Props = SearchResultTagsProps;


/**
 * Article search result tag list component.
 *
 * @param props - See [[SearchResultTagsProps]].
 */
const SearchResultTags: React.FC<Props> = function(props) {
    var tagLis: React.ReactElement[] = [];
    for (const tag of props.searchResult.tags) {
        tagLis.push(
            <li key={tag} className='tag-badge'>{tag}</li>
        );
    }

    return (
        <ul className='article-tags'>
            {tagLis}
        </ul>
    );
};

export default SearchResultTags;
