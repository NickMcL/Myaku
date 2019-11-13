/**
 * SearchOptionsCollapseToggle component module. See
 * [[SearchOptionsCollapseToggle]].
 */

import React from 'react';

/** Props for the [[SearchOptionsCollapseToggle]] component. */
interface SearchOptionsCollapseToggleProps {
    /**
     * Whether the search options are currently collapsed or not.
     *
     * @remarks
     * The toggle will indicate that the search options will be shown by
     * toggling if this is true, and the toggle will indicate that the search
     * options will be hidden by toggling if this is false.
     */
    collapsed: boolean;

    /** Callback to call whether the toggle is clicked. */
    onToggle: () => void;
}
type Props = SearchOptionsCollapseToggleProps;

/**
 * Toggle button component for showing/hiding the search options in a form.
 *
 * @param props - See [[SearchOptionsCollapseProps]].
 */
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
