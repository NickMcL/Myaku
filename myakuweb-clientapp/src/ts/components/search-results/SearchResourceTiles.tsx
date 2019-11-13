/**
 * SearchResourceTiles component module. See [[SearchResourceTiles]].
 */

import React from 'react';
import ResourceLinkSetTile from
    'ts/components/search-results/ResourceLinkSetTile';
import { SearchResources } from 'ts/types/types';
import Tile from 'ts/components/generic/Tile';

/** Props for the [[SearchResourceTiles]] component. */
interface SearchResourceTilesProps {
    /**
     * The search resources content to render in the component.
     *
     * If null, will render loading tiles in place of the tiles containing the
     * search resources content.
     */
    resources: SearchResources | null;
}
type Props = SearchResourceTilesProps;

/**
 * Number of loading tiles to render when the resources given to the component
 * are null.
 */
const LOADING_TILE_COUNT = 3;


/**
 * Get the header tile element for the search resources tiles.
 *
 * @returns The header tile element.
 */
function getHeaderTile(): React.ReactElement {
    var classList = ['aside-tile', 'resource-header-tile'];
    return (
        <Tile tileClasses={classList.join(' ')}>
            <h4>More Resources</h4>
        </Tile>
    );
}

/**
 * Get an array of resource link set tiles for the given resources.
 *
 * If the given resources are null, returns an array of loading tiles instead.
 *
 * @param resources - The resources to get resource link set tiles for.
 *
 * @returns - The resource link set tiles, or loading tiles if resources is
 * null.
 */
function getResourceLinkSetTiles(
    resources: SearchResources | null
): React.ReactNodeArray {
    var linkSetTiles: React.ReactElement[] = [];
    if (resources) {
        for (const linkSet of resources.resourceLinkSets) {
            linkSetTiles.push(
                <ResourceLinkSetTile
                    key={linkSet.setName}
                    query={resources.query}
                    linkSet={linkSet}
                />
            );
        }
    } else {
        for (let i = 0; i < LOADING_TILE_COUNT; ++i) {
            linkSetTiles.push(
                <ResourceLinkSetTile
                    key={i}
                    query={null}
                    linkSet={null}
                />
            );
        }
    }
    return linkSetTiles;
}

/**
 * Aside component for additional resource tiles to accompy with search
 * results.
 *
 * @param props - See [[SearchResourceTilesProps]].
 */
const SearchResourceTiles: React.FC<Props> = function(props) {
    return (
        <aside className='resource-links-aside'>
            {getHeaderTile()}
            {getResourceLinkSetTiles(props.resources)}
        </aside>
    );
};

export default SearchResourceTiles;
