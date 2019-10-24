/** @module Content tile */

import React from 'react';

interface TileProps {
    children: React.ReactNode;
    tileClasses?: string;
}

const Tile: React.FC<TileProps> = function(props) {
    var tileClasses = 'tile';
    if (props.tileClasses) {
        tileClasses += ` ${props.tileClasses}`;
    }

    return (
        <section className={tileClasses}>
            {props.children}
        </section>
    );
};

export default Tile;
