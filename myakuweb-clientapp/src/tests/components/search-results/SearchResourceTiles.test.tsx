/**
 * Tests for the [[SearchResourceTiles]] component.
 */

import React from 'react';
import SearchResourceTiles from
    'ts/components/search-results/SearchResourceTiles';
import { shallow } from 'enzyme';

import {
    SEARCH_RESOURCES_NO,
    SEARCH_RESOURCES_OB,
} from 'tests/testData';


describe('<SearchResourceTiles />', function() {
    it('renders correctly with resources set', function() {
        const wrapper = shallow(
            <SearchResourceTiles
                resources={SEARCH_RESOURCES_NO}
            />
        );
        expect(wrapper).toMatchSnapshot();

        wrapper.setProps({resources: SEARCH_RESOURCES_OB});
        expect(wrapper).toMatchSnapshot();
    });

    it('renders correctly with no resources set', function() {
        const wrapper = shallow(
            <SearchResourceTiles
                resources={null}
            />
        );
        expect(wrapper).toMatchSnapshot();

        wrapper.setProps({resources: SEARCH_RESOURCES_NO});
        expect(wrapper).toMatchSnapshot();
    });
});
