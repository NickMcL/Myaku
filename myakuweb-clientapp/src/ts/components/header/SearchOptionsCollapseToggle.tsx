/** @module Toggle button component for showing/hiding the search options */

import React from 'react';

interface SearchOptionsCollapseToggleProps {
    collapsed: boolean;
    onToggle: () => void;
}
type Props = SearchOptionsCollapseToggleProps;


const SearchOptionsCollapseToggle: React.FC<Props> = function(props) {
    var buttonText;
    if (props.collapsed) {
        buttonText = 'Show search options';
    } else {
        buttonText = 'Hide search options';
    }

    return (
        <button
            className='button-link search-options-toggle'
            type='button'
            onClick={props.onToggle}
        >
            {buttonText}
        </button>
    );
};

export default SearchOptionsCollapseToggle;
