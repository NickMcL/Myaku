/**
 * Tests for the SearchOptionsInput component.
 * @module tests/components/header/SearchOptionsInput.test
 */

import { KanaConvertType } from 'ts/types/types';
import KanaConvertTypeInput from 'ts/components/header/KanaConvertTypeInput';
import React from 'react';
import SearchOptionsInput from 'ts/components/header/SearchOptionsInput';
import { expectComponent } from 'tests/testUtils';

import {
    ShallowWrapper,
    shallow,
} from 'enzyme';

function callKanaConvertTypeInputOnChange(
    wrapper: ShallowWrapper, value: KanaConvertType
): void {
    const input = wrapper.find(KanaConvertTypeInput);
    expect(input).toHaveLength(1);
    input.props().onChange(value);
}


describe('<SearchOptionsInput />', function() {
    it('renders correctly', function() {
        const wrapper = shallow(
            <SearchOptionsInput
                searchOptions={{'kanaConvertType': 'hira'}}
                onChange={(): void => {}}
            />
        );
        expect(wrapper).toMatchSnapshot();
    });

    it('forwards KanaConvertType value', function() {
        const wrapper = shallow(
            <SearchOptionsInput
                searchOptions={{'kanaConvertType': 'hira'}}
                onChange={(): void => {}}
            />
        );
        expectComponent(wrapper, KanaConvertTypeInput, {
            kanaConvertType: 'hira',
            onChange: expect.any(Function),
        });

        wrapper.setProps({'searchOptions': {'kanaConvertType': 'kata'}});
        expectComponent(wrapper, KanaConvertTypeInput, {
            kanaConvertType: 'kata',
            onChange: expect.any(Function),
        });

        wrapper.setProps({'searchOptions': {'kanaConvertType': 'none'}});
        expectComponent(wrapper, KanaConvertTypeInput, {
            kanaConvertType: 'none',
            onChange: expect.any(Function),
        });

        wrapper.setProps({'searchOptions': {'kanaConvertType': 'hira'}});
        expectComponent(wrapper, KanaConvertTypeInput, {
            kanaConvertType: 'hira',
            onChange: expect.any(Function),
        });
    });

    it('calls onChange when KanaConvertType onChange called', function() {
        const mockOnChange = jest.fn();
        const wrapper = shallow(
            <SearchOptionsInput
                searchOptions={{'kanaConvertType': 'hira'}}
                onChange={mockOnChange}
            />
        );

        callKanaConvertTypeInputOnChange(wrapper, 'kata');
        expect(mockOnChange).toBeCalledTimes(1);
        expect(mockOnChange).lastCalledWith('kanaConvertType', 'kata');

        callKanaConvertTypeInputOnChange(wrapper, 'none');
        expect(mockOnChange).toBeCalledTimes(2);
        expect(mockOnChange).lastCalledWith('kanaConvertType', 'none');

        callKanaConvertTypeInputOnChange(wrapper, 'hira');
        expect(mockOnChange).toBeCalledTimes(3);
        expect(mockOnChange).lastCalledWith('kanaConvertType', 'hira');
    });
});
