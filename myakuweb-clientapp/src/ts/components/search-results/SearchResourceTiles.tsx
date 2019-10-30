/**
 * @module Additional resource tiles to accompy with a search result component
 */

import React from 'react';
import ResourceLinkSetTile from
    'ts/components/search-results/ResourceLinkSetTile';
import { SearchResources } from 'ts/types/types';
import Tile from 'ts/components/generic/Tile';

interface SearchResourceTilesProps {
    resources: SearchResources | null;
}
type Props = SearchResourceTilesProps;

const LOADING_TILE_COUNT = 3;


function getHeaderTile(): React.ReactElement {
    var classList = ['aside-tile', 'resource-header-tile'];
    return (
        <Tile tileClasses={classList.join(' ')}>
            <h4>More Resources</h4>
        </Tile>
    );
}

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

const SearchResourceTiles: React.FC<Props> = function(props) {
    return (
        <aside className='resource-links-aside'>
            {getHeaderTile()}
            {getResourceLinkSetTiles(props.resources)}
        </aside>
    );
};

export default SearchResourceTiles;
