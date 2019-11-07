/**
 * Tests for the GettingStartedTile component.
 * @module tests/components/start/GettingStartedTile.test
 */

import GettingStartedTile from 'ts/components/start/GettingStartedTile';
import React from 'react';
import { shallow } from 'enzyme';


describe('<GettingStartedTile />', function() {
    it('renders correctly', function() {
        const wrapper = shallow(<GettingStartedTile />);
        expect(wrapper).toMatchSnapshot();
    });
});
