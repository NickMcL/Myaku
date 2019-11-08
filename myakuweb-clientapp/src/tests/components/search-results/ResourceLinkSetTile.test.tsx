/**
 * Tests for the ResourceLinkSetTile component.
 * @module tests/components/search-results/ResourceLinkSetTile.test
 */

import React from 'react';
import ResourceLinkSetTile from
    'ts/components/search-results/ResourceLinkSetTile';
import { shallow } from 'enzyme';

import {
    SEARCH_RESOURCES_NO,
    SEARCH_RESOURCES_OB,
} from 'tests/testData';

describe('<ResourceLinkSetTile />', function() {
    it('renders correctly with resources set', function() {
        const wrapper = shallow(
            <ResourceLinkSetTile
                query={SEARCH_RESOURCES_NO.query}
                linkSet={SEARCH_RESOURCES_NO.resourceLinkSets[0]}
            />
        );
        expect(wrapper).toMatchSnapshot();

        wrapper.setProps({
            query: SEARCH_RESOURCES_OB.query,
            linkSet: SEARCH_RESOURCES_OB.resourceLinkSets[0],
        });
        expect(wrapper).toMatchSnapshot();
    });

    it('renders correctly with no resources set', function() {
        const wrapper = shallow(
            <ResourceLinkSetTile
                query={null}
                linkSet={null}
            />
        );
        expect(wrapper).toMatchSnapshot();

        wrapper.setProps({
            query: SEARCH_RESOURCES_NO.query,
            linkSet: SEARCH_RESOURCES_NO.resourceLinkSets[0],
        });
        expect(wrapper).toMatchSnapshot();
    });
});
