/**
 * Tests for the [[KanaConvertTypeInput]] component.
 */

import KanaConvertTypeInput from 'ts/components/header/KanaConvertTypeInput';
import React from 'react';

import {
    HTMLAttributes,
    ReactWrapper,
    mount,
} from 'enzyme';
import {
    KanaConvertType,
    isKanaConvertType,
} from 'ts/types/types';

const LABEL_TEXT_MAP: Record<KanaConvertType, string> = {
    'hira': 'Hiragana',
    'kata': 'Katakana',
    'none': 'No conversion',
};

function expectRadioChecked(
    wrapper: ReactWrapper, checkedValue: KanaConvertType
): void {
    var seenValues: string[] = [];
    var checkedValueFound = false;
    wrapper.find('input').forEach(
        function(node: ReactWrapper<HTMLAttributes>) {
            const nodeValue = node.props().value;
            if (typeof nodeValue !== 'string') {
                throw new Error(
                    `Radio input value is not a string: ${nodeValue}`
                );
            }
            expect(seenValues).not.toContain(nodeValue);
            seenValues.push(nodeValue);

            if (nodeValue === checkedValue) {
                checkedValueFound = true;
                expect(node.props().checked).toBe(true);
            } else {
                expect(node.props().checked).toBe(false);
            }
        }
    );

    expect(checkedValueFound).toBe(true);
}

function simulateRadioInputChange(
    wrapper: ReactWrapper, value: KanaConvertType
): void {
    const inputWrapper = wrapper.find(`input[value="${value}"]`);
    expect(inputWrapper).toHaveLength(1);

    inputWrapper.simulate('change');
}


describe('<KanaConvertTypeInput />', function() {
    it('has correct labels for inputs', function() {
        const wrapper = mount(
            <KanaConvertTypeInput
                kanaConvertType={'hira'}
                onChange={(): void => {}}
            />
        );
        wrapper.find('input').forEach(
            function(node: ReactWrapper<HTMLAttributes>) {
                const label = wrapper.find(
                    `label[htmlFor="${node.props().id}"]`
                );
                expect(label).toHaveLength(1);

                const nodeValue = node.props().value;
                if (!isKanaConvertType(nodeValue)) {
                    throw new Error(
                        'Radio input value is not a valid kana convert '
                        + `type: "${nodeValue}"`
                    );
                }
                expect(label.text()).toStrictEqual(
                    expect.stringContaining(LABEL_TEXT_MAP[nodeValue])
                );
            }
        );
    });

    it('renders correct checked input', function() {
        const wrapper = mount(
            <KanaConvertTypeInput
                kanaConvertType={'hira'}
                onChange={(): void => {}}
            />
        );
        expect(wrapper).toMatchSnapshot();
        expectRadioChecked(wrapper, 'hira');

        wrapper.setProps({kanaConvertType: 'kata'});
        expect(wrapper).toMatchSnapshot();
        expectRadioChecked(wrapper, 'kata');

        wrapper.setProps({kanaConvertType: 'none'});
        expect(wrapper).toMatchSnapshot();
        expectRadioChecked(wrapper, 'none');

        wrapper.setProps({kanaConvertType: 'hira'});
        expect(wrapper).toMatchSnapshot();
        expectRadioChecked(wrapper, 'hira');
    });

    it('calls onChange on radio input change', function() {
        const mockOnChange = jest.fn();
        const wrapper = mount(
            <KanaConvertTypeInput
                kanaConvertType={'hira'}
                onChange={mockOnChange}
            />
        );
        simulateRadioInputChange(wrapper, 'kata');
        expect(mockOnChange).toBeCalledTimes(1);
        expect(mockOnChange).lastCalledWith('kata');

        simulateRadioInputChange(wrapper, 'none');
        expect(mockOnChange).toBeCalledTimes(2);
        expect(mockOnChange).lastCalledWith('none');

        simulateRadioInputChange(wrapper, 'hira');
        expect(mockOnChange).toBeCalledTimes(3);
        expect(mockOnChange).lastCalledWith('hira');
    });
});
