/** @module Tile with sample searches */

import React from 'react';
import Tile from './Tile';

interface GettingStartedTileProps {
    tileClasses?: string;
}

interface SampleSearch {
    query: string;
    explanation: string;
}

const SAMPLE_SEARCHES: SampleSearch[] = [
    {
        query: '力士',
        explanation: 'A normal word',
    },
    {
        query: '非常に激しい雨',
        explanation: 'A set phrase',
    },
    {
        query: '急がば回れ',
        explanation: 'A proverb',
    },
    {
        query: '歯が立たない',
        explanation: 'An idiom',
    },
];

var GettingStartedTile: React.FC<GettingStartedTileProps> = function(props) {
    var sampleSearchElements: React.ReactNodeArray = [];
    for (const sampleSearch of SAMPLE_SEARCHES) {
        sampleSearchElements.push(
            <li key={sampleSearch.query}>
                {`${sampleSearch.explanation} - `}
                <span className='japanese-text' lang='ja'>
                    <a href={'/?q=' + sampleSearch.query}>
                        {sampleSearch.query}
                    </a>
                </span>
            </li>
        );
    }

    return (
        <Tile tileClasses={props.tileClasses}>
            <h4 className='main-tile-header'>Getting Started</h4>
            <p className='list-start-text'>
                Here are some sample searches to get started:
            </p>
            <ul className='myaku-ul'>
                {sampleSearchElements}
            </ul>
        </Tile>
    );
};

export default GettingStartedTile;
