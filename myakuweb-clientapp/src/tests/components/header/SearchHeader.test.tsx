/**
 * Tests for the [[SearchHeader]] component.
 */

import HeaderNav from 'ts/components/header/HeaderNav';
import HeaderSearchForm from 'ts/components/header/HeaderSearchForm';
import React from 'react';
import SearchHeader from 'ts/components/header/SearchHeader';
import { createMemoryHistory } from 'history';
import { expectComponent } from 'tests/testUtils';
import { mount } from 'enzyme';


jest.mock('ts/components/header/HeaderNav', () => jest.fn(() => null));
jest.mock('ts/components/header/HeaderSearchForm', () => jest.fn(() => null));

describe('<SearchHeader />', function() {
    it('renders correctly', function() {
        const history = createMemoryHistory();
        const wrapper = mount(
            <SearchHeader
                loadingSearch={false}
                history={history}
                location={history.location}
            />
        );
        expectComponent(wrapper, HeaderNav, {});
        expectComponent(
            wrapper, HeaderSearchForm,
            {
                'loadingSearch': false,
                'history': expect.anything(),
                'location': expect.anything(),
            }
        );
    });
});
