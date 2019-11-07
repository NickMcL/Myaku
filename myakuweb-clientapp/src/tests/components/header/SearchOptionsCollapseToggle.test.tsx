/**
 * Tests for the SearchOptionsCollapseToggle component.
 * @module tests/components/header/SearchOptionsCollapseToggle.test
 */

import React from 'react';
import SearchOptionsCollapseToggle from
    'ts/components/header/SearchOptionsCollapseToggle';

import {
    ReactWrapper,
    mount,
} from 'enzyme';

function expectButtonText(wrapper: ReactWrapper, collapsed: boolean): void {
    const button = wrapper.find('button');
    expect(button).toHaveLength(1);

    if (collapsed) {
        expect(button.text()).toStrictEqual(expect.stringContaining('Show'));
        expect(button.text()).not.toStrictEqual(
            expect.stringContaining('Hide')
        );
    } else {
        expect(button.text()).toStrictEqual(expect.stringContaining('Hide'));
        expect(button.text()).not.toStrictEqual(
            expect.stringContaining('Show')
        );
    }
}

function simulateButtonClick(wrapper: ReactWrapper): void {
    const button = wrapper.find('button');
    expect(button).toHaveLength(1);
    button.simulate('click');
}


describe('<SearchOptionsCollapseToggle />', function() {
    it('has text that matches collapsed state', function() {
        const wrapper = mount(
            <SearchOptionsCollapseToggle
                collapsed
                onToggle={(): void => {}}
            />
        );
        expect(wrapper).toMatchSnapshot();
        expectButtonText(wrapper, true);

        wrapper.setProps({'collapsed': false});
        expect(wrapper).toMatchSnapshot();
        expectButtonText(wrapper, false);

        wrapper.setProps({'collapsed': true});
        expect(wrapper).toMatchSnapshot();
        expectButtonText(wrapper, true);
    });

    it('calls onToggle on button click', function() {
        const mockOnToggle = jest.fn();
        const wrapper = mount(
            <SearchOptionsCollapseToggle
                collapsed
                onToggle={mockOnToggle}
            />
        );
        simulateButtonClick(wrapper);
        expect(mockOnToggle).toBeCalledTimes(1);

        simulateButtonClick(wrapper);
        expect(mockOnToggle).toBeCalledTimes(2);

        wrapper.setProps({'collapsed': false});
        simulateButtonClick(wrapper);
        expect(mockOnToggle).toBeCalledTimes(3);

        simulateButtonClick(wrapper);
        expect(mockOnToggle).toBeCalledTimes(4);
    });
});
