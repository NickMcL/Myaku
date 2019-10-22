/** @module Tile with sample searches component */

import React from 'react';
import Tile from './Tile';

import {
    DEFAULT_SEARCH_OPTIONS,
    Search,
} from '../types';

interface GettingStartedTileProps {
    onSearchSubmit: (search: Search) => void;
}
type Props = GettingStartedTileProps;

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


function getSearchSubmitHandler(
    query: string, onSearchSubmit: (search: Search) => void
): (event: React.SyntheticEvent) => void {
    return function(event: React.SyntheticEvent): void {
        event.preventDefault();
        onSearchSubmit({
            query: query,
            pageNum: 1,
            options: DEFAULT_SEARCH_OPTIONS,
        });
    };
}

function getSampleSearchLis(
    onSearchSubmit: (search: Search) => void
): React.ReactElement[] {
    var sampleSearchLis: React.ReactElement[] = [];
    for (const sampleSearch of SAMPLE_SEARCHES) {
        sampleSearchLis.push(
            <li key={sampleSearch.query}>
                {`${sampleSearch.explanation} - `}
                <span className='japanese-text' lang='ja'>
                    <a
                        href={`/?q=${sampleSearch.query}`}
                        onClick={getSearchSubmitHandler(
                            sampleSearch.query, onSearchSubmit
                        )}
                    >
                        {sampleSearch.query}
                    </a>
                </span>
            </li>
        );
    }
    return sampleSearchLis;
}

const GettingStartedTile: React.FC<Props> = function(props) {
    return (
        <Tile tileClasses='start-tile'>
            <h4 className='main-tile-header'>Getting Started</h4>
            <p className='list-start-text'>
                Here are some sample searches to get started:
            </p>
            <ul className='myaku-ul'>
                {getSampleSearchLis(props.onSearchSubmit)}
            </ul>
        </Tile>
    );
};

export default GettingStartedTile;
