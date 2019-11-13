/**
 * Header component module. See [[Header]].
 */

import React from 'react';

/** Props for the [[Header]] component. */
interface HeaderProps {
    /** Child nodes to wrap in the header container. */
    children: React.ReactNode;
}

/**
 * Fixed-width header container component.
 *
 * @param props - See [[HeaderProps]].
 */
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
