/**
 * ResourceLinkSetTile component module. See [[ResourceLinkSetTile]].
 */

import React from 'react';
import { ResourceLinkSet } from 'ts/types/types';
import Tile from 'ts/components/generic/Tile';

/** Props for the [[ResourceLinkSetTile]] component. */
interface ResourceLinkSetTileProps {
    /**
     * Search query that the given resource link sets are for. Will be
     * displayed in the rendered link text for each resource link.
     *
     * If null, a loading tile will be rendered in place of the resource link
     * set tile.
     */
    query: string | null;

    /**
     * Resource link set whose links to render in the component.
     *
     * If null, a loading tile will be rendered in place of the resource link
     * set tile.
     */
    linkSet: ResourceLinkSet | null;
}
type Props = ResourceLinkSetTileProps;

/** The height of the loading tiles rendered by the component. */
const LOADING_HEIGHT = '6.625rem';


/**
 * Get the li elements to render for each link in a resource link set.
 *
 * @param linkSet - Resource link set whose resource links to get li elements
 * for.
 * @param query - Search query that the resource link set is for. Will be
 * displayed in the rendered link text in each resource link li element.
 *
 * @returns The resource link li elements for the given resource link set.
 */
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

/**
 * Component for a tile containing a resource link set.
 *
 * Will return a loading tile instead if any of the props are null.
 *
 * @param props - See [[ResourceLinkSetTileProps]].
 */
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
