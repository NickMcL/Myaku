/** @module Start page content for MyakuWeb */

import GettingStartedTile from 'ts/components/start-page/GettingStartedTile';
import React from 'react';
import { Search } from 'ts/types/types';
import WhatIsMyakuTile from 'ts/components/start-page/WhatIsMyakuTile';

interface StartContentProps {
    onSearchSubmit: (search: Search) => void;
}
type Props = StartContentProps;

const StartContent: React.FC<Props> = function(props) {
    return (
        <div className='start-tile-container'>
            <WhatIsMyakuTile />
            <GettingStartedTile onSearchSubmit={props.onSearchSubmit} />
        </div>
    );
};

export default StartContent;
