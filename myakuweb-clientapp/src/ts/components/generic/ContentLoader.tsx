/**
 * Animated content loading indicator component.
 * @module ts/components/generic/ContentLoader
 */

import React from 'react';


const ContentLoader: React.FC<{}> = function() {
    return (
        <div className='content-loader-dots'>
            <div></div>
            <div></div>
            <div></div>
        </div>
    );
};

export default ContentLoader;
