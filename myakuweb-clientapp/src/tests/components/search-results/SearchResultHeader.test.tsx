/**
 * Tests for the SearchResultHeader component.
 * @module tests/components/search-results/SearchResultHeader.test
 */

import { BASELINE_SEARCH_RESULT_PAGE } from 'tests/testData';
import React from 'react';
import SearchResultHeader from
    'ts/components/search-results/SearchResultHeader';
import { shallow } from 'enzyme';


describe('<SearchResultHeader />', function() {
    it('renders correctly', function() {
        const wrapper = shallow(
            <SearchResultHeader
                searchResult={BASELINE_SEARCH_RESULT_PAGE.results[0]}
            />
        );
        expect(wrapper).toMatchSnapshot();

        wrapper.setProps({
            searchResult: BASELINE_SEARCH_RESULT_PAGE.results[1],
        });
        expect(wrapper).toMatchSnapshot();
    });
});
