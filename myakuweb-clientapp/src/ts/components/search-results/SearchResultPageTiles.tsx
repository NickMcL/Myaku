/**
 * SearchResultPageTiles component module. See [[SearchResultPageTiles]].
 */

import React from 'react';
import SearchResultPageHeader from
    'ts/components/search-results/SearchResultPageHeader';
import SearchResultPageNav from
    'ts/components/search-results/SearchResultPageNav';
import SearchResultTile from
    'ts/components/search-results/SearchResultTile';

import {
    Search,
    SearchResultPage,
} from 'ts/types/types';

/** Props for the [[SearchResultPageTiles]] component. */
interface SearchResultPageTilesProps {
    /**
     * The requested search for the result page.
     *
     * Used to create the header tile for the result tiles. If null, the header
     * tile will be a generic header without any information specific to the
     * search.
     */
    requestedSearch: Search | null;

    /**
     * The total result count for the search for the result page.
     *
     * Displayed in the header tile for the result tiles. If null, a loading
     * block will be displayed in its place in the header instead.
     */
    totalResults: number | null;

    /**
     * The search result page whose content to display in the result page
     * tiles.
     *
     * If null, loading tiles will be displayed instead of the result page
     * tiles.
     */
    resultPage: SearchResultPage | null;
}
type Props = SearchResultPageTilesProps;

/** Number of loading tiles to display if the resultPage prop is null */
export const LOADING_TILE_COUNT = 10;

/**
 * Max page number to display in the header tile.
 *
 * If the page number for the requestedSearch prop is greater than this number,
 * this number will be displayed in the header instead.
 */
export const MAX_DISPLAY_PAGE_NUM = 99;


/**
 * Get the page number to display in the header tile.
 *
 * If the resultPage prop is not null, uses the page number from the search
 * specified in that object.
 * Otherwise, uses the page number specified in the requestedSearch prop if it
 * is not null and is within the [[MAX_DISPLAY_PAGE_NUM]].
 *
 * @param props - The props given to the SearchResultPageTiles component.
 *
 * @returns The page number to display in the header tile. If null, it means no
 * page number should be displayed.
 */
function getHeaderPageNum(props: Props): number | null {
    if (props.resultPage !== null) {
        return props.resultPage.search.pageNum;
    }
    if (props.requestedSearch === null) {
        return null;
    }
    if (props.requestedSearch.pageNum > MAX_DISPLAY_PAGE_NUM) {
        return MAX_DISPLAY_PAGE_NUM;
    }
    return props.requestedSearch.pageNum;
}

/**
 * Get the search result tiles to display.
 *
 * @param props - The props given to the SearchResultPageTiles component.
 *
 * @returns The search result tiles to display. If the resultPage prop is null,
 * loading tiles will be returned instead of search result tiles.
 */
function getSearchResultTiles(props: Props): React.ReactElement[] {
    var tiles: React.ReactElement[] = [];
    if (props.resultPage === null) {
        for (let i = 0; i < LOADING_TILE_COUNT; ++i) {
            tiles.push(
                <SearchResultTile
                    key={i}
                    searchQuery={null}
                    searchResult={null}
                />
            );
        }
    } else {
        for (const result of props.resultPage.results) {
            tiles.push(
                <SearchResultTile
                    key={result.articleId}
                    searchQuery={props.resultPage.search.query}
                    searchResult={result}
                />
            );
        }
    }
    return tiles;
}

/**
 * Get the page nav tile to display.
 *
 * Will return a non-null page nav tile only if the resultPage prop is not null
 * and the totalResults prop is greater than 0.
 *
 * @param props - The props given to the SearchResultPageTiles component.
 *
 * @returns The page nav tile to display. If null, it means no page nav tile
 * should be displayed.
 */
function getPageNav(props: Props): React.ReactNode {
    if (props.resultPage === null || props.totalResults === 0) {
        return null;
    }

    return (
        <SearchResultPageNav
            search={props.resultPage.search}
            hasNextPage={props.resultPage.hasNextPage}
            maxPageReached={props.resultPage.maxPageReached}
        />
    );
}

/**
 * Component for displaying search result page data as tiles.
 *
 * @param props - See [[SearchResultPageTilesProps]].
 */
const SearchResultPageTiles: React.FC<Props> = function(props) {
    return (
        <div className='result-tile-container'>
            <SearchResultPageHeader
                totalResults={props.totalResults}
                pageNum={getHeaderPageNum(props)}
            />
            {getSearchResultTiles(props)}
            {getPageNav(props)}
        </div>
    );
};

export default SearchResultPageTiles;
