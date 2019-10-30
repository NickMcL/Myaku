/**
 * Start page content for MyakuWeb.
 * @module ts/components/start/StartContent
 */

import GettingStartedTile from 'ts/components/start/GettingStartedTile';
import React from 'react';
import WhatIsMyakuTile from 'ts/components/start/WhatIsMyakuTile';
import { useEffect } from 'react';


const StartContent: React.FC<{}> = function() {
    useEffect(function() {
        document.title = 'Myaku';
    }, []);

    return (
        <div className='start-tile-container'>
            <WhatIsMyakuTile />
            <GettingStartedTile />
        </div>
    );
};

export default StartContent;
