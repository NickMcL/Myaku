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
    maxQueryLength: number;
    errorValueSubmitted: boolean;
    onChange: (searchQuery: string) => void;
}
type Props = SearchBarInputProps;

const enum ErrorState {
    OK,
    Warning,
    Error
}

// Search box placeholder text adjusts based on viewport size
const FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.';
const SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.';
const DEFAULT_PLACEHOLDER = SHORT_SEARCH_PLACEHOLDER;
const VIEWPORT_PLACEHOLDERS = {
    [ViewportSize.Small]: FULL_SEARCH_PLACEHOLDER,
};


function useSearchInput(
    currentValue: string, handleChange: (value: string) => void,
    errorState: ErrorState
): React.ReactElement {
    const placeholder = useViewportReactiveValue(
        DEFAULT_PLACEHOLDER, VIEWPORT_PLACEHOLDERS
    );

    var classList = ['search-input'];
    if (errorState === ErrorState.Warning) {
        classList.push('warning-border');
    } else if (errorState === ErrorState.Error) {
        classList.push('error-border');
    }

    return (
        <input
            className={classList.join(' ')}
            id='search-input'
            type='text'
            name='q'
            aria-label='Search input'
            value={currentValue}
            placeholder={placeholder}
            onChange={useInputChangeHandler(handleChange)}
        />
    );
}

function useSearchClearButton(
    handleChange: (value: string) => void
): React.ReactElement {
    return (
        <button
            className='search-clear'
            type='button'
            aria-label='Search clear'
            onClick={useInputClearHandler(handleChange)}
        >
            <i className='fa fa-times'></i>
        </button>
    );
}

function getSearchSubmitButton(): React.ReactElement {
    return (
        <button
            className='search-submit'
            type='submit'
            aria-label='Search submit button'
        >
            <i className='fa fa-search'></i>
        </button>
    );
}

function getErrorMessageElement(
    inputtedQuery: string, maxQueryLength: number, errorState: ErrorState
): React.ReactElement | null {
    if (
        errorState === ErrorState.OK
        || inputtedQuery.length <= maxQueryLength
    ) {
        return null;
    }

    var className = 'input-warning-text';
    var action = 'Inputted';
    if (errorState === ErrorState.Error) {
        action = 'Submitted';
        className = 'input-error-text';
    }
    return (
        <p className={className}>
            <span>{`${action} query is too long `}</span>
            <span>
                {`(${inputtedQuery.length} / ${maxQueryLength} characters)`}
            </span>
        </p>
    );
}

function getErrorState(
    inputtedValue: string, maxValueLength: number, submittedErrorValue: boolean
): ErrorState {
    if (submittedErrorValue) {
        return ErrorState.Error;
    } else if (inputtedValue.length > maxValueLength) {
        return ErrorState.Warning;
    } else {
        return ErrorState.OK;
    }
}

const SearchBarInput: React.FC<Props> = function(props) {
    const errorState = getErrorState(
        props.searchQuery, props.maxQueryLength, props.errorValueSubmitted
    );
    return (
        <React.Fragment>
            <div className='search-bar'>
                {useSearchInput(props.searchQuery, props.onChange, errorState)}
                {useSearchClearButton(props.onChange)}
                {getSearchSubmitButton()}
            </div>
            {getErrorMessageElement(
                props.searchQuery, props.maxQueryLength, errorState
            )}
        </React.Fragment>
    );
};

export default SearchBarInput;
