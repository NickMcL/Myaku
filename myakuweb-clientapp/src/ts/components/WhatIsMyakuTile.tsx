/** @module Tile with an explation of the MyakuWeb site */

import React from 'react';
import Tile from './Tile';

interface WhatIsMyakuTileProps {
    tileClasses?: string;
}

var WhatIsMyakuTile: React.FC<WhatIsMyakuTileProps> = function(props) {
    return (
        <Tile tileClasses={props.tileClasses}>
            <h4 className='main-tile-header'>What is Myaku?</h4>
            <p>
                <span className='key-word'>Myaku</span> is a tool for learning
                Japanese from context.
            </p>
            <p>
                {
                    'It helps develop a natural feel for Japanese by showing '
                    + 'in what '
                }
                <span className='key-word'>context</span>
                {' natives use it today.'}
            </p>

            <p className='list-start-text'>It works like this:</p>
            <ol className='myaku-ol'>
                <li>Search for a Japanese term of interest.</li>
                <li>
                    Get ranked links to select Japanese articles showing real
                    usage of the term.
                </li>
                <li>
                    Gain a natural feel for how the term is used by checking
                    out the articles.
                </li>
            </ol>
        </Tile>
    );
};

export default WhatIsMyakuTile;
