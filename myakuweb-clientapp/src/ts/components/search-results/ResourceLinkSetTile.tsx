/** @module Resource link set tile component */

import React from 'react';
import { ResourceLinkSet } from 'ts/types/types';
import Tile from 'ts/components/generic/Tile';

interface ResourceLinkSetTileProps {
    query: string | null;
    linkSet: ResourceLinkSet | null;
}
type Props = ResourceLinkSetTileProps;

const LOADING_HEIGHT = '6.625rem';


function getResourceLinkLis(
    linkSet: ResourceLinkSet, query: string
): React.ReactNodeArray {
    var resourceLinkLis: React.ReactElement[] = [];
    for (const resourceLink of linkSet.resourceLinks) {
        resourceLinkLis.push(
            <li key={resourceLink.resourceName}>
                <a href={resourceLink.link}>
                    {`Search ${resourceLink.resourceName} for `}
                    <span lang='ja'>
                        {query}
                    </span>
                </a>
            </li>
        );
    }
    return resourceLinkLis;
}

const ResourceLinkSetTile: React.FC<Props> = function(props) {
    var classList = ['aside-tile', 'resource-links-tile'];
    if (props.query === null || props.linkSet === null) {
        return (
            <Tile
                tileClasses={classList.join(' ')}
                loadingHeight={LOADING_HEIGHT}
            />
        );
    }

    return (
        <Tile tileClasses={classList.join(' ')}>
            <h5>
                {props.linkSet.setName}
            </h5>
            <ul className='resource-links-list'>
                {getResourceLinkLis(props.linkSet, props.query)}
            </ul>
        </Tile>
    );
};

export default ResourceLinkSetTile;
