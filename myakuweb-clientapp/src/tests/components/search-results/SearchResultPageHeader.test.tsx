/**
 * Tests for the [[SearchResultPageHeader]] component.
 */

import React from 'react';
import SearchResultPageHeader from
    'ts/components/search-results/SearchResultPageHeader';

import {
    render,
    shallow,
} from 'enzyme';


describe('<SearchResultPageHeader />', function() {
    it(
        'renders correctly with null total results/null page num',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    totalResults={null}
                    pageNum={null}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it(
        'renders correctly with non-null total results/null page num',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    totalResults={155}
                    pageNum={null}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it(
        'renders correctly with null total results/non-null page num',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    totalResults={null}
                    pageNum={1}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it(
        'renders correctly with non-null total results/non-null page num',
        function() {
            const wrapper = shallow(
                <SearchResultPageHeader
                    totalResults={155}
                    pageNum={1}
                />
            );
            expect(wrapper).toMatchSnapshot();
        }
    );

    it('does not show page num if 0 total results', function() {
        const wrapper = shallow(
            <SearchResultPageHeader
                totalResults={0}
                pageNum={1}
            />
        );
        expect(wrapper).toMatchSnapshot();
    });

    it('uses int comma for total results and page num', function() {
        const wrapper = render(
            <SearchResultPageHeader
                totalResults={3444555}
                pageNum={1222}
            />
        );
        expect(wrapper.text()).toStrictEqual(
            expect.stringContaining('3,444,555 found')
        );
        expect(wrapper.text()).toStrictEqual(
            expect.stringContaining('Page 1,222')
        );
    });
});
