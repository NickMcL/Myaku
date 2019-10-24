/** @module Tile footer button component */

import React from 'react';

interface TileFooterButtonProps {
    children: React.ReactNode;
    onClick: () => void;
}
type Props = TileFooterButtonProps;


const TileFooterButton: React.FC<Props> = function(props) {
    return (
        <footer className='tile-footer'>
            <button
                className='button-link tile-footer-button'
                type='button'
                onClick={props.onClick}
            >
                {props.children}
            </button>
        </footer>
    );
};

export default TileFooterButton;
