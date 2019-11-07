/**
 * Tests for the Header component.
 * @module tests/components/header/Header.test
 */

import Header from 'ts/components/header/Header';
import React from 'react';
import { mount } from 'enzyme';


describe('<Header />', function() {
    it('renders correctly', function() {
        const wrapper = mount(
            <Header>
                <div>Header content 1</div>
                <div>Header content 2</div>
            </Header>
        );
        expect(wrapper).toMatchSnapshot();
    });
});
