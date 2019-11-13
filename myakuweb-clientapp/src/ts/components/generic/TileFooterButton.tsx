/**
 * TileFooterButton component module. See [[TileFooterButton]].
 */

import React from 'react';

/** Props for the [[TileFooterButton]] component. */
interface TileFooterButtonProps {
    /** Child nodes to show within the tile footer button. */
    children: React.ReactNode;

    /** Callback for when the tile footer button is clicked. */
    onClick: () => void;
}
type Props = TileFooterButtonProps;

/**
 * Component for a footer button for a tile that spans the full width of the
 * tile.
 *
 * @param props - See [[TileFooterButtonProps]].
 */
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
