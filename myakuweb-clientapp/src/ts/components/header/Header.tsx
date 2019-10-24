/** @module MyakuWeb main header component */

import React from 'react';

interface HeaderProps {
    children: React.ReactNode;
}

const Header: React.FC<HeaderProps> = function(props) {
    return (
        <header className='page-header'>
            <div className='content-container header-content-container'>
                {props.children}
            </div>
        </header>
    );
};

export default Header;
