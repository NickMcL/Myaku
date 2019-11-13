/**
 * SearchOptionsInput component module. See [[SearchOptionsInput]].
 */

import KanaConvertTypeInput from 'ts/components/header/KanaConvertTypeInput';
import React from 'react';

import { KanaConvertType, SearchOptions } from 'ts/types/types';

/**
 * Generic search option onChange function that takes any valid key-value
 * search option pair as its arguments.
 */
interface OnChangeFunc {
    // </> comment is to stop JSX syntax highlighting from applying
    <K extends keyof SearchOptions> /* </> */ (
        changedOption: K, newValue: SearchOptions[K]
    ): void;
}

/** Props for the [[SearchOptionsInput]] component. */
interface SearchOptionsInputProps {
    /**
     * Current inputted search options for the form containing this component.
     *
     * These options will be displayed as selected in the search option inputs
     * rendered by the component.
     */
    searchOptions: SearchOptions;

    /**
     * Callback to call with a new value for a search option whenever any
     * search option value changes.
     */
    onChange: OnChangeFunc;
}
type Props = SearchOptionsInputProps;


/**
 * Wrapper component for all search option input components.
 *
 * @param props - See [[SearchOptionsInputProps]].
 */
const SearchOptionsInput: React.FC<Props> = function(props) {
    function handleKanaConvertTypeChange(newValue: KanaConvertType): void {
        props.onChange<'kanaConvertType'>('kanaConvertType', newValue);
    }

    return (
        <KanaConvertTypeInput
            kanaConvertType={props.searchOptions.kanaConvertType}
            onChange={handleKanaConvertTypeChange}
        />
    );
};

export default SearchOptionsInput;
