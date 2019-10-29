/** @module Nav component for the main MyakuWeb header */

import { Link } from 'react-router-dom';
import React from 'react';
import myakuLogoUrl from 'images/myaku-logo.svg';

const MYAKU_GITHUB_LINK = 'https://github.com/FriedRice/Myaku';


const HeaderNav: React.FC<{}> = function() {
    return (
        <nav className='header-nav'>
            <Link to='/' className='nav-logo'>
                <img
                    className='myaku-logo'
                    src={myakuLogoUrl}
                    alt='Myaku logo'
                />
            </Link>
            <ul className='nav-link-list'>
                <li>
                    <a aria-label='Myaku GitHub' href={MYAKU_GITHUB_LINK}>
                        Github
                    </a>
                </li>
            </ul>
        </nav>
    );
};

export default HeaderNav;
