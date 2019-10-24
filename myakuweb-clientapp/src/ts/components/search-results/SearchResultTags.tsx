/** @module Search result tag list component */

import { ArticleSearchResult } from 'ts/types/types';
import React from 'react';

interface SearchResultTagsProps {
    searchResult: ArticleSearchResult;
}
type Props = SearchResultTagsProps;


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
