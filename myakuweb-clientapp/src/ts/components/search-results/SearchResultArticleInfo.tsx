/**
 * SearchResultArticleInfo component module. See [[SearchResultArticleInfo]].
 */

import { ArticleSearchResult } from 'ts/types/types';
import React from 'react';

import {
    getDaysBetween,
    humanizeDate,
} from 'ts/app/utils';

/** Props for the [[SearchResultArticleInfo]] component. */
interface SearchResultArticleInfoProps {
    searchResult: ArticleSearchResult;
}
type Props = SearchResultArticleInfoProps;


/**
 * Make a time element for the given date.
 *
 * @param date - Date to make a time element for.
 *
 * @returns The time element made for the date.
 */
function makeTimeElement(date: Date): React.ReactElement {
    return (
        <time dateTime={date.toISOString()}>
            {humanizeDate(date)}
        </time>
    );
}

/**
 * Determine if last updated datetime should be displayed for the search
 * result.
 *
 * The last updated datetime is not worth displaying if it's close to the
 * publication date.
 *
 * Additionally, if the publication date is older, the amount of time between
 * publication and the update must be greater in order for the update to be
 * worth displaying.
 *
 * @param searchResult - Search result to determine if its last updated
 * datetime should be displayed.
 *
 * @returns True if the last updated datetime should be displayed, or false if
 * it shouldn't be displayed.
 */
function shouldDisplayLastUpdatedDate(
    searchResult: ArticleSearchResult
): boolean {
    if (searchResult.lastUpdatedDatetime === null) {
        return false;
    }

    var now = new Date();
    var daysSincePublish = getDaysBetween(
        now,
        searchResult.publicationDatetime
    );
    var daysSinceUpdate = getDaysBetween(
        now,
        searchResult.lastUpdatedDatetime
    );
    var daysUpdatedAfter = getDaysBetween(
        searchResult.lastUpdatedDatetime,
        searchResult.publicationDatetime
    );

    if (daysUpdatedAfter < 1 || daysSincePublish <= 7) {
        return false;
    }

    if (
        daysSinceUpdate <= 7
        || daysSincePublish < 180 && daysUpdatedAfter > 30
        || daysSincePublish < 365 && daysUpdatedAfter > 90
        || daysSincePublish < 365 * 2 && daysUpdatedAfter > 180
        || daysUpdatedAfter > 365
    ) {
        return true;
    }

    return false;
}

/**
 * Search result article info list component.
 *
 * @param props - See [[SearchResultArticleInfoProps]].
 */
const SearchResultArticleInfo: React.FC<Props> = function(props) {
    var lastUpdatedDatetimeLi: React.ReactElement | null = null;
    if (shouldDisplayLastUpdatedDate(props.searchResult)) {
        lastUpdatedDatetimeLi = (
            <li key='updated-datetime' className='updated-datetime'>
                {'Updated '}
                {makeTimeElement(
                    props.searchResult.lastUpdatedDatetime as Date
                )}
            </li>
        );
    }

    return (
        <ul className='article-info'>
            <li key='source-name'>
                {props.searchResult.sourceName}
            </li>
            <li key='publication-datetime'>
                {makeTimeElement(props.searchResult.publicationDatetime)}
            </li>
            {lastUpdatedDatetimeLi}
            <li key='instance-count'>
                {props.searchResult.instanceCount.toLocaleString('en-US')}
                {' instances'}
            </li>
        </ul>
    );
};

export default SearchResultArticleInfo;
