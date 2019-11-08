/**
 * Tests for the SearchFailedTile component.
 * @module tests/components/search-results/SearchFailedTile.test
 */

import React from 'react';
import SearchFailedTile from 'ts/components/search-results/SearchFailedTile';

import {
    mount,
    shallow,
} from 'enzyme';


describe('<SearchFailedTile />', function() {
    it('renders correctly', function() {
        const wrapper = shallow(<SearchFailedTile />);
        expect(wrapper).toMatchSnapshot();
    });

    it('sets document title', function() {
        mount(<SearchFailedTile />);
        expect(document.title).toBe('Search Failed');
    });
});
