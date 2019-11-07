/**
 * Tests for the StartContent component.
 * @module tests/components/start/StartContent.test
 */

import { MemoryRouter } from 'react-router-dom';
import React from 'react';
import StartContent from 'ts/components/start/StartContent';

import {
    mount,
    shallow,
} from 'enzyme';


describe('<StartContent />', function() {
    it('renders correctly', function() {
        const wrapper = shallow(<StartContent />);
        expect(wrapper).toMatchSnapshot();
    });

    it('sets document title', function() {
        mount(
            <MemoryRouter>
                <StartContent />
            </MemoryRouter>
        );
        expect(document.title).toBe('Myaku');
    });
});
