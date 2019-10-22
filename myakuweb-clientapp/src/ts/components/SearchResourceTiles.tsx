/**
 * @module Additional resource tiles to accompy with a search result component
 */

import React from 'react';
import ResourceLinkSetTile from './ResourceLinkSetTile';
import { SearchResources } from '../types';
import Tile from './Tile';

interface SearchResourceTilesProps {
    resources: SearchResources;
}
type Props = SearchResourceTilesProps;


const SearchResourceTiles: React.FC<Props> = function(props) {
    var linkSetTiles: React.ReactElement[] = [];
    for (const linkSet of props.resources.resourceLinkSets) {
        linkSetTiles.push(
            <ResourceLinkSetTile
                key={linkSet.setName}
                query={props.resources.query}
                linkSet={linkSet}
            />
        );
    }

    return (
        <aside className='resource-links-aside'>
            <Tile tileClasses='aside-tile resource-header-tile'>
                <h4>More Resources</h4>
            </Tile>
            {linkSetTiles}
        </aside>
    );
};

export default SearchResourceTiles;
