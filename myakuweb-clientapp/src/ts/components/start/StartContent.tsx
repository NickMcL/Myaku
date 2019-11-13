/**
 * StartContent component module. See [[StartContent]].
 */

import GettingStartedTile from 'ts/components/start/GettingStartedTile';
import React from 'react';
import WhatIsMyakuTile from 'ts/components/start/WhatIsMyakuTile';
import { useEffect } from 'react';

/**
 * Start page content component.
 *
 * Sets the document title as well.
 *
 * @remarks
 * This component has no props.
 */
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
