/** @module Start page content for MyakuWeb */

import GettingStartedTile from './GettingStartedTile';
import React from 'react';
import WhatIsMyakuTile from './WhatIsMyakuTile';

const StartContent: React.FC<{}> = function() {
    return (
        <div className='start-tile-container'>
            <WhatIsMyakuTile tileClasses='start-tile' />
            <GettingStartedTile tileClasses='start-tile' />
        </div>
    );
};

export default StartContent;
