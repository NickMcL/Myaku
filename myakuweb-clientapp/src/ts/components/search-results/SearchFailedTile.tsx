/**
 * SearchFailedTile component module. See [[SearchFailedTile]].
 */

import React from 'react';
import Tile from 'ts/components/generic/Tile';
import { useEffect } from 'react';


/**
 * Search failure notice tile component.
 *
 * Sets the document title to indicate search failure as well.
 *
 * @remarks
 * This component has no props.
 */
const SearchFailedTile: React.FC<{}> = function() {
    useEffect(function() {
        document.title = 'Search Failed';
    }, []);

    return (
        <div className='start-tile-container'>
            <Tile tileClasses='start-tile'>
                <h4 className='error-text'>Search Failed</h4>
                <p>
                    There was an issue connecting to the server to make the
                    search.
                </p>
                <p>Please attempt the search again later.</p>
            </Tile>
        </div>
    );
};

export default SearchFailedTile;
