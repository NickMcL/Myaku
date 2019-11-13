/**
 * Tests for the [[SearchResultSampleText]] component.
 */

import { BASELINE_SEARCH_RESULT_PAGE } from 'tests/testData';
import React from 'react';
import SearchResultSampleText from
    'ts/components/search-results/SearchResultSampleText';
import { shallow } from 'enzyme';


describe('<SearchResultSampleText />', function() {
    it('renders correctly', function() {
        const testResult = BASELINE_SEARCH_RESULT_PAGE.results[0];
        const wrapper = shallow(
            <SearchResultSampleText
                sampleText={testResult.mainSampleText}
            />
        );
        expect(wrapper).toMatchSnapshot();

        wrapper.setProps({sampleText: testResult.moreSampleTexts[0]});
        expect(wrapper).toMatchSnapshot();
    });
});
