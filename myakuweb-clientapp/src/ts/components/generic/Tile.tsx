/** @module Content tile */

import React from 'react';

interface TileProps {
    children?: React.ReactNode;
    tileClasses?: string;
    loadingHeight?: string;
}
type Props = TileProps;


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
