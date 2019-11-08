/**
 * Tests for the SearchResultTags component.
 * @module tests/components/search-results/SearchResultTags.test
 */

import { BASELINE_SEARCH_RESULT_PAGE } from 'tests/testData';
import React from 'react';
import SearchResultTags from 'ts/components/search-results/SearchResultTags';
import { shallow } from 'enzyme';


describe('<SearchResultTags />', function() {
    it('renders correctly', function() {
        const testResults = BASELINE_SEARCH_RESULT_PAGE.results;
        const wrapper = shallow(
            <SearchResultTags
                searchResult={testResults[0]}
            />
        );
        expect(wrapper).toMatchSnapshot();

        wrapper.setProps({searchResult: testResults[1]});
        expect(wrapper).toMatchSnapshot();
    });
});
