/**
 * Tests for the WhatIsMyakuTile component.
 * @module tests/components/start/WhatIsMyakuTile.test
 */

import React from 'react';
import WhatIsMyakuTile from 'ts/components/start/WhatIsMyakuTile';
import { shallow } from 'enzyme';


describe('<WhatIsMyakuTile />', function() {
    it('renders correctly', function() {
        const wrapper = shallow(<WhatIsMyakuTile />);
        expect(wrapper).toMatchSnapshot();
    });
});
