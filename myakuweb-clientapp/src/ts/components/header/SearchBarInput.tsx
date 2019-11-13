/**
 * SearchBarInput component module. See [[SearchBarInput]].
 */

import React from 'react';
import { ViewportSize } from 'ts/app/viewport';
import { useCallback } from 'react';
import useInputChangeHandler from 'ts/hooks/useInputChangeHandler';
import useViewportReactiveValue from 'ts/hooks/useViewportReactiveValue';

/** Props for the [[SearchBarInput]] component. */
interface SearchBarInputProps {
    /**
     * Current inputted search query for the form containing the search bar.
     * This will be displayed in the search input.
     */
    searchQuery: string;

    /**
     * If true, an animated loading icon will be displayed inside the submit
     * button, and if false, a normal search icon will be displayed.
     *
     * Also, if true, the search bar input will be set to readonly, and the
     * clear and submit buttons will be disabled.
     */
    loading: boolean;

    /**
     * If the searchQuery prop has a length longer than this value, a warning
     * or error message will be displayed.
     *
     * @remarks
     * Whether the displayed message is a warning or error depends on the value
     * of the errorValueSubmitted prop.
     */
    maxQueryLength: number;

    /**
     * If true AND the searchQuery prop either has a length of 0 or a length
     * greater than the maxQueryLength prop, an error message will be
     * displayed.
     *
     * If false and the searchQuery prop has a length greater than
     * maxQueryLength prop, a warning message will be displayed instead of an
     * error message.
     */
    errorValueSubmitted: boolean;

    /**
     * Callback to call with the new search query value whenever it changes.
     */
    onChange: (searchQuery: string) => void;
}
type Props = SearchBarInputProps;

/**
 * The different error states that the component can be in depending on the
 * given props.
 */
const enum ErrorState {
    OK,
    Warning,
    Error
}

/** Search input placeholder text adjusts based on viewport size */
const FULL_SEARCH_PLACEHOLDER = 'Japanese word, set phrase, idiom, etc.';
const SHORT_SEARCH_PLACEHOLDER = 'Japanese word, phrase, etc.';
const DEFAULT_PLACEHOLDER = SHORT_SEARCH_PLACEHOLDER;
const VIEWPORT_PLACEHOLDERS = {
    [ViewportSize.Small]: FULL_SEARCH_PLACEHOLDER,
};


/**
 * Hook for getting the search input element for the search bar.
 *
 * @remarks
 * The placeholder text for the input will change based on the viewport size.
 *
 * @param currentValue - The value that should be set for the search input
 * element.
 * @param handleChange - Callback to call with the new input value whenever it
 * changes.
 * @param loading - Whether the search bar is in a loading state or not. If
 * true, the search input will be set as readonly.
 * @param errorState - The current error state of the search bar. If Warning or
 * Error, the border color of the input will be changes to yellow or red
 * respectively.
 *
 * @returns The search input element to use in the search bar.
 */
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

/**
 * Hook for getting the search clear button for the search bar.
 *
 * @remarks
 * The button will blur focus after being clicked.
 *
 * @param handleInputChange - Callback to call with the new search input value
 * whenever it changes. Will be called with an empty string whenever the clear
 * button is clicked.
 * @param loading - Whether the search bar is in a loading state or not. If
 * true, the search clear button will be set as disabled.
 *
 * @returns The search clear button element to use in the search bar.
 */
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

/**
 * Get the search submit button for the search bar.
 *
 * @param loading - Whether the search bar is in a loading state or not. If
 * true, the search submit button will be set as disabled, and an animated
 * loading icon will be displayed within it instead of the normal search icon.
 *
 * @returns The search submit button element to use in the search bar.
 */
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

/**
 * Get the error text element for a zero length query error.
 *
 * @param className - Value to set as the className for the error text element.
 *
 * @returns The error text element.
 */
function getNoQueryErrorElement(className: string): React.ReactElement {
    return <p className={className}>No search query entered</p>;
}

/**
 * Get the error text element for a query longer than max length error.
 *
 * @param className - Value to set as the className for the error text element.
 * @param inputtedQuery - The currently inputted search query.
 * @param maxQueryLength - The max allowable length of the query.
 * @param errorState - The current error state of search bar. If Warning/OK,
 * displays the query as 'Inputted' in the error message, and if Error,
 * displays the query as 'Submitted' in the error message.
 *
 * @returns The error text element.
 */
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

/**
 * Get the error message element for the currently inputted search query.
 *
 * @param inputtedQuery - The currently inputted search query.
 * @param maxQueryLength - The max allowable length of the query.
 * @param errorState - The current error state of the search bar.
 *
 * @returns If errorState is OK or the inputtedQuery is not empty and within
 * the maxQueryLength, returns null.
 * Otherwise, returns the error message element that the search bar should
 * display.
 */
function getErrorMessageElement(
    inputtedQuery: string, maxQueryLength: number, errorState: ErrorState
): React.ReactElement | null {
    var className;
    if (errorState == ErrorState.Error) {
        className = 'input-error-text';
    } else if (errorState == ErrorState.Warning) {
        className = 'input-warning-text';
    } else {
        return null;
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

/**
 * Get the current error state of the search bar.
 *
 * @param inputtedQuery - The currently inputted search query.
 * @param maxQueryLength - The max allowable length of the query.
 * @param submittedErrorValue - Whether an error value has been submitted for
 * the form containing the search bar or not.
 *
 * @returns The current error state of the search bar.
 */
function getErrorState(
    inputtedQuery: string, maxQueryLength: number, submittedErrorValue: boolean
): ErrorState {
    if (inputtedQuery.length > 0 && inputtedQuery.length <= maxQueryLength) {
        return ErrorState.OK;
    }

    if (submittedErrorValue) {
        return ErrorState.Error;
    }

    if (inputtedQuery.length > maxQueryLength) {
        return ErrorState.Warning;
    }

    return ErrorState.OK;
}

/**
 * Search bar input component with submit and input clear buttons.
 *
 * @param props - See [[SearchBarInputProps]].
 */
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
