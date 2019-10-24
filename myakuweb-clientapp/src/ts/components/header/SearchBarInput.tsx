/**
 * Search bar input component with submit and input clear buttons.
 * @module ts/components/header/SearchBarInput
 */

import React from 'react';
import { ViewportSize } from 'ts/app/viewport';
import useInputChangeHandler from 'ts/hooks/useInputChangeHandler';
import useInputClearHandler from 'ts/hooks/useInputClearHandler';
import useViewportReactiveValue from 'ts/hooks/useViewportReactiveValue';

interface SearchBarInputProps {
    searchQuery: string;
    onChange: (searchQuery: string) => void;
}
type Props = SearchBarInputProps;

// Search box placeholder text adjusts based on viewport size
const FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.';
const SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.';
const DEFAULT_PLACEHOLDER = SHORT_SEARCH_PLACEHOLDER;
const VIEWPORT_PLACEHOLDERS = {
    [ViewportSize.Medium]: FULL_SEARCH_PLACEHOLDER,
};


const SearchBarInput: React.FC<Props> = function(props) {
    const placeholder = useViewportReactiveValue<string>(
        DEFAULT_PLACEHOLDER, VIEWPORT_PLACEHOLDERS
    );

    return (
        <div className='search-bar'>
            <input
                className='search-input'
                id='search-input'
                type='text'
                name='q'
                aria-label='Search input'
                value={props.searchQuery}
                placeholder={placeholder}
                onChange={useInputChangeHandler(props.onChange)}
            />
            <button
                className='search-clear'
                type='button'
                aria-label='Search clear'
                onClick={useInputClearHandler(props.onChange)}
            >
                <i className='fa fa-times'></i>
            </button>
            <button
                className='search-submit'
                type='submit'
                aria-label='Search submit button'
            >
                <i className='fa fa-search'></i>
            </button>
        </div>
    );
};

export default SearchBarInput;
