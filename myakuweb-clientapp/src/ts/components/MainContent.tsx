/** @module Main content container for MyakuWeb */

import React from 'react';

interface MainContentProps {
    children: React.ReactNode;
}

const MainContent: React.FC<MainContentProps> = function(props) {
    return (
        <main className='content-container'>
            {props.children}
        </main>
    );
};

export default MainContent;
