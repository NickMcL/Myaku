/** @module Start page content for MyakuWeb */

import GettingStartedTile from './GettingStartedTile';
import React from 'react';
import { Search } from '../types';
import WhatIsMyakuTile from './WhatIsMyakuTile';

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
