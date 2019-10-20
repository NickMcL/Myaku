/** @module Wrapper for all search options input components  */

import KanaConvertTypeInput from './KanaConvertTypeInput';
import React from 'react';
import { KanaConvertType, SearchOptions } from '../types';

interface OnChangeFunc {
    <K extends keyof SearchOptions> /* </> */ (
        changedOption: K, newValue: SearchOptions[K]
    ): void;
}

interface SearchOptionsInputProps {
    searchOptions: SearchOptions;
    onChange: OnChangeFunc;
}
type Props = SearchOptionsInputProps;


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
