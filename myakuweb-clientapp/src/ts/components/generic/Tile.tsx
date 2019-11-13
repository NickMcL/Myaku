/**
 * Tile component module. See [[Tile]].
 */

import React from 'react';

/** Props for the [[Tile]] component. */
interface TileProps {
    /** Child nodes to show within the tile. */
    children?: React.ReactNode;

    /** Additional classes to apply to the tile container element. */
    tileClasses?: string;

    /**
     * If given, will ignore the children prop and render an animated loading
     * tile with the given height instead.
     */
    loadingHeight?: string;
}
type Props = TileProps;


/**
 * Content tile container component.
 *
 * @param props - See [[TileProps]].
 */
const Tile: React.FC<Props> = function(props) {
    var tileClasses = ['tile'];
    if (props.tileClasses) {
        tileClasses.push(props.tileClasses);
    }

    if (props.loadingHeight) {
        tileClasses.push('loading');
        const style: React.CSSProperties = {
            width: '100%',
            height: props.loadingHeight,
        };
        return (
            <section className={tileClasses.join(' ')} style={style}></section>
        );
    } else {
        return (
            <section className={tileClasses.join(' ')}>
                {props.children || null}
            </section>
        );
    }
};

export default Tile;
