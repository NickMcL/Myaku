/** @module Nav component for the main MyakuWeb header */

import React from 'react';
import myakuLogoUrl from 'images/myaku-logo.svg';

interface HeaderNavProps {
    onReturnToStart: () => void;
}
type Props = HeaderNavProps;

const MYAKU_GITHUB_LINK = 'https://github.com/FriedRice/Myaku';


const HeaderNav: React.FC<Props> = function(props) {
    function handleReturnToStart(event: React.SyntheticEvent): void {
        event.preventDefault();
        props.onReturnToStart();
    }

    return (
        <nav className='header-nav'>
            <a className='nav-logo' href='/' onClick={handleReturnToStart}>
                <img
                    className='myaku-logo'
                    src={myakuLogoUrl}
                    alt='Myaku logo'
                />
            </a>
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
