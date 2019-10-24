/** @module Resource link set tile component */

import React from 'react';
import { ResourceLinkSet } from 'ts/types/types';
import Tile from 'ts/components/generic/Tile';

interface ResourceLinkSetTileProps {
    query: string;
    linkSet: ResourceLinkSet;
}
type Props = ResourceLinkSetTileProps;


const ResourceLinkSetTile: React.FC<Props> = function(props) {
    var resourceLinkLis: React.ReactElement[] = [];
    for (const resourceLink of props.linkSet.resourceLinks) {
        resourceLinkLis.push(
            <li key={resourceLink.resourceName}>
                <a href={resourceLink.link}>
                    {`Search ${resourceLink.resourceName} for `}
                    <span className='japanese-text' lang='ja'>
                        {props.query}
                    </span>
                </a>
            </li>
        );
    }

    return (
        <Tile tileClasses='aside-tile resource-links-tile'>
            <h5>
                {props.linkSet.setName}
            </h5>
            <ul className='resource-links-list'>
                {resourceLinkLis}
            </ul>
        </Tile>
    );
};

export default ResourceLinkSetTile;
