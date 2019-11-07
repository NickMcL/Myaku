/**
 * Tests for the HeaderNav component.
 * @module tests/components/header/HeaderNav.test
 */

import HeaderNav from 'ts/components/header/HeaderNav';
import React from 'react';
import { shallow } from 'enzyme';


describe('<HeaderNav />', function() {
    it('renders correctly', function() {
        const wrapper = shallow(<HeaderNav />);
        expect(wrapper).toMatchSnapshot();
    });
});
