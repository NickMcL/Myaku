/**
 * Tests for the SearchBarInput component.
 * @module tests/components/header/SearchBarInputInput.test
 */

import React from 'react';
import SearchBarInput from 'ts/components/header/SearchBarInput';

import {
    HTMLAttributes,
    ReactWrapper,
    mount,
} from 'enzyme';

function getInput(wrapper: ReactWrapper): ReactWrapper<HTMLAttributes> {
    const input = wrapper.find('input');
    expect(input).toHaveLength(1);
    return input;
}

function getClearButton(wrapper: ReactWrapper): ReactWrapper<HTMLAttributes> {
    const button = wrapper.find('button.search-clear');
    expect(button).toHaveLength(1);
    return button;
}

function getSubmitButton(wrapper: ReactWrapper): ReactWrapper<HTMLAttributes> {
    const button = wrapper.find('button.search-submit');
    expect(button).toHaveLength(1);
    return button;
}

function getErrorMessageText(
    wrapper: ReactWrapper, errorMessageClass: string
): string {
    const errorMessageElement = wrapper.find(`.${errorMessageClass}`);
    expect(errorMessageElement).toHaveLength(1);
    return errorMessageElement.text();
}


var wrapper = mount(<div />);
beforeEach(function() {
    wrapper = mount(
        <SearchBarInput
            searchQuery={'test'}
            loading={false}
            maxQueryLength={100}
            errorValueSubmitted={false}
            onChange={(): void => {}}
        />
    );
});

describe('<SearchBarInput />', function() {
    it('renders correctly', function() {
        expect(wrapper).toMatchSnapshot();
    });

    it('sets search query as input value', function() {
        expect(getInput(wrapper).props().value).toBe('test');

        wrapper.setProps({searchQuery: ''});
        expect(getInput(wrapper).props().value).toBe('');

        wrapper.setProps({searchQuery: 'backagain'});
        expect(getInput(wrapper).props().value).toBe('backagain');
    });

    it('disables input and buttons when loading', function() {
        expect(getInput(wrapper).props().readOnly).toBe(false);
        expect(getClearButton(wrapper).props().disabled).toBe(false);
        expect(getSubmitButton(wrapper).props().disabled).toBe(false);

        wrapper.setProps({loading: true});
        expect(getInput(wrapper).props().readOnly).toBe(true);
        expect(getClearButton(wrapper).props().disabled).toBe(true);
        expect(getSubmitButton(wrapper).props().disabled).toBe(true);

        wrapper.setProps({loading: false});
        expect(getInput(wrapper).props().readOnly).toBe(false);
        expect(getClearButton(wrapper).props().disabled).toBe(false);
        expect(getSubmitButton(wrapper).props().disabled).toBe(false);
    });

    it('shows loading spinner when loading', function() {
        expect(
            getSubmitButton(wrapper).find('.content-loading-query-spinner')
        ).toHaveLength(0);
        expect(getSubmitButton(wrapper).find('i.fa-search')).toHaveLength(1);

        wrapper.setProps({loading: true});
        expect(
            getSubmitButton(wrapper).find('.content-loading-query-spinner')
        ).toHaveLength(1);
        expect(getSubmitButton(wrapper).find('i.fa-search')).toHaveLength(0);

        wrapper.setProps({loading: false});
        expect(
            getSubmitButton(wrapper).find('.content-loading-query-spinner')
        ).toHaveLength(0);
        expect(getSubmitButton(wrapper).find('i.fa-search')).toHaveLength(1);
    });

    it('shows inputted query too long warning', function() {
        wrapper.setProps({maxQueryLength: 15});

        expect(wrapper.find('.input-warning-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('warning-border')).toBe(false);

        wrapper.setProps({searchQuery: 'this-query-is-to-long'});
        const errorMessage = getErrorMessageText(
            wrapper, 'input-warning-text'
        );
        expect(errorMessage).toMatch(/Inputted/);
        expect(errorMessage).toMatch(/too long/);
        expect(errorMessage).toMatch(/21 \/ 15/);
        expect(getInput(wrapper).hasClass('warning-border')).toBe(true);

        wrapper.setProps({searchQuery: 'short-query'});
        expect(wrapper.find('.input-warning-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('warning-border')).toBe(false);
    });

    it('shows submitted query too long error', function() {
        wrapper.setProps({maxQueryLength: 15});

        expect(wrapper.find('.input-error-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('error-border')).toBe(false);

        wrapper.setProps({searchQuery: 'this-query-is-to-long'});
        expect(wrapper.find('.input-error-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('error-border')).toBe(false);

        wrapper.setProps({errorValueSubmitted: true});
        const errorMessage = getErrorMessageText(wrapper, 'input-error-text');
        expect(errorMessage).toMatch(/Submitted/);
        expect(errorMessage).toMatch(/too long/);
        expect(errorMessage).toMatch(/21 \/ 15/);
        expect(getInput(wrapper).hasClass('error-border')).toBe(true);

        wrapper.setProps({errorValueSubmitted: false});
        expect(wrapper.find('.input-error-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('error-border')).toBe(false);

        wrapper.setProps({searchQuery: 'short-query'});
        expect(wrapper.find('.input-error-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('error-border')).toBe(false);
    });

    it('shows submitted empty query error', function() {
        wrapper.setProps({searchQuery: ''});

        expect(wrapper.find('.input-error-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('error-border')).toBe(false);

        wrapper.setProps({errorValueSubmitted: true});
        const errorMessage = getErrorMessageText(wrapper, 'input-error-text');
        expect(errorMessage).toMatch(/No search query entered/);
        expect(getInput(wrapper).hasClass('error-border')).toBe(true);

        wrapper.setProps({errorValueSubmitted: false});
        expect(wrapper.find('.input-error-text')).toHaveLength(0);
        expect(getInput(wrapper).hasClass('error-border')).toBe(false);
    });

    it('ignores submitted error if query is valid', function() {
        wrapper.setProps({errorValueSubmitted: true});

        const input = getInput(wrapper);
        expect(input.hasClass('error-border')).toBe(false);
        expect(input.hasClass('warning-border')).toBe(false);

        expect(wrapper.find('.input-error-text')).toHaveLength(0);
        expect(wrapper.find('.input-warning-text')).toHaveLength(0);
    });

    it('calls onChange when input entered', function() {
        const mockOnChange = jest.fn();
        wrapper.setProps({onChange: mockOnChange});

        getInput(wrapper).getDOMNode<HTMLInputElement>().value = 'test2';
        getInput(wrapper).simulate('change');
        expect(mockOnChange).toBeCalledTimes(1);
        expect(mockOnChange).lastCalledWith('test2');

        getInput(wrapper).getDOMNode<HTMLInputElement>().value = 'test';
        getInput(wrapper).simulate('change');
        expect(mockOnChange).toBeCalledTimes(2);
        expect(mockOnChange).lastCalledWith('test');

        getInput(wrapper).getDOMNode<HTMLInputElement>().value = '';
        getInput(wrapper).simulate('change');
        expect(mockOnChange).toBeCalledTimes(3);
        expect(mockOnChange).lastCalledWith('');
    });

    it('calls onChange when input cleared', function() {
        const mockOnChange = jest.fn();
        wrapper.setProps({onChange: mockOnChange});

        getClearButton(wrapper).simulate('click');
        expect(mockOnChange).toBeCalledTimes(1);
        expect(mockOnChange).lastCalledWith('');

        getClearButton(wrapper).simulate('click');
        expect(mockOnChange).toBeCalledTimes(2);
        expect(mockOnChange).lastCalledWith('');
    });

    it('blurs focus on input clear button click', function() {
        const clearButtonElement = (
            getClearButton(wrapper).getDOMNode<HTMLButtonElement>()
        );
        clearButtonElement.focus();
        expect(document.activeElement).toBe(clearButtonElement);

        getClearButton(wrapper).simulate('click');
        expect(document.activeElement).not.toBe(clearButtonElement);
    });
});
