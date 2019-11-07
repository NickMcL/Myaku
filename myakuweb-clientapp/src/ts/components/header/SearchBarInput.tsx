/**
 * Search bar input component with submit and input clear buttons.
 * @module ts/components/header/SearchBarInput
 */

import React from 'react';
import { ViewportSize } from 'ts/app/viewport';
import { useCallback } from 'react';
import useInputChangeHandler from 'ts/hooks/useInputChangeHandler';
import useViewportReactiveValue from 'ts/hooks/useViewportReactiveValue';

interface SearchBarInputProps {
    searchQuery: string;
    loading: boolean;
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
    loading: boolean, errorState: ErrorState
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
            readOnly={loading}
            onChange={useInputChangeHandler(handleChange)}
        />
    );
}

function useSearchClearButton(
    handleInputChange: (value: string) => void, loading: boolean
): React.ReactElement {
    const handleInputClear = useCallback(
        function(event: React.SyntheticEvent<HTMLButtonElement>): void {
            event.currentTarget.blur();
            handleInputChange('');
        },
        [handleInputChange]
    );

    return (
        <button
            className='search-clear'
            type='button'
            aria-label='Search clear'
            disabled={loading}
            onClick={handleInputClear}
        >
            <i className='fa fa-times'></i>
        </button>
    );
}

function getSearchSubmitButton(loading: boolean): React.ReactElement {
    var icon = <i className='fa fa-search'></i>;
    if (loading) {
        icon = <div className='content-loading-query-spinner'></div>;
    }
    return (
        <button
            className='search-submit'
            type='submit'
            aria-label='Search submit button'
            disabled={loading}
        >
            {icon}
        </button>
    );
}

function getNoQueryErrorElement(className: string): React.ReactElement {
    return <p className={className}>No search query entered</p>;
}

function getQueryTooLongErrorElement(
    className: string, inputtedQuery: string, maxQueryLength: number,
    errorState: ErrorState
): React.ReactElement {
    var action = 'Inputted';
    if (errorState === ErrorState.Error) {
        action = 'Submitted';
    }
    return (
        <p className={className}>
            <span>{`${action} search query is too long `}</span>
            <span>
                {`(${inputtedQuery.length} / ${maxQueryLength} characters)`}
            </span>
        </p>
    );
}

function getErrorMessageElement(
    inputtedQuery: string, maxQueryLength: number, errorState: ErrorState
): React.ReactElement | null {
    var className;
    if (errorState == ErrorState.Error) {
        className = 'input-error-text';
    } else {
        className = 'input-warning-text';
    }

    if (inputtedQuery.length === 0) {
        return getNoQueryErrorElement(className);
    } else if (inputtedQuery.length > maxQueryLength) {
        return getQueryTooLongErrorElement(
            className, inputtedQuery, maxQueryLength, errorState
        );
    } else {
        return null;
    }
}

function getErrorState(
    inputtedValue: string, maxValueLength: number, submittedErrorValue: boolean
): ErrorState {
    if (inputtedValue.length > 0 && inputtedValue.length <= maxValueLength) {
        return ErrorState.OK;
    }

    if (submittedErrorValue) {
        return ErrorState.Error;
    } else {
        return ErrorState.Warning;
    }
}

const SearchBarInput: React.FC<Props> = function(props) {
    const errorState = getErrorState(
        props.searchQuery, props.maxQueryLength, props.errorValueSubmitted
    );
    return (
        <React.Fragment>
            <div className='search-bar'>
                {useSearchInput(
                    props.searchQuery, props.onChange, props.loading,
                    errorState
                )}
                {useSearchClearButton(props.onChange, props.loading)}
                {getSearchSubmitButton(props.loading)}
            </div>
            {getErrorMessageElement(
                props.searchQuery, props.maxQueryLength, errorState
            )}
        </React.Fragment>
    );
};

export default SearchBarInput;
