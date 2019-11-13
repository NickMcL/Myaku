/**
 * Enzyme setup for React component testing.
 */

import ReactSixteenAdapter from 'enzyme-adapter-react-16';
import { configure } from 'enzyme';

configure({
    adapter: new ReactSixteenAdapter(),
});
