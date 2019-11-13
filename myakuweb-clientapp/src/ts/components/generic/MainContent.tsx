/**
 * MainContent component module. See [[MainContent]].
 */

import React from 'react';

/** Props for the [[MainContent]] component. */
interface MainContentProps {
    /** Child nodes to wrap in the main content container. */
    children: React.ReactNode;
}

/**
 * Main page content container component.
 *
 * @param props - See [[MainContentProps]].
 */
const MainContent: React.FC<MainContentProps> = function(props) {
    return (
        <main className='content-container'>
            {props.children}
        </main>
    );
};

export default MainContent;
