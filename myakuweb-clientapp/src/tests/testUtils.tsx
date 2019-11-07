/**
 * Utility functions for use in React component Jest tests.
 * @module tests/testUtils
 */

import {
    ComponentType,
    ReactWrapper,
    ShallowWrapper,
} from 'enzyme';


export function expectComponent<C, P>(
    wrapper: ReactWrapper<C> | ShallowWrapper<C>,
    component: ComponentType<P>, propKeyValues: object
): void {
    const componentWrapper = wrapper.find(component);
    expect(componentWrapper).toHaveLength(1);

    const componentProps = componentWrapper.props() as Partial<P>;
    const expectedKeyCount = Object.keys(propKeyValues).length;
    expect(Object.keys(componentProps)).toHaveLength(expectedKeyCount);
    expect(componentProps).toStrictEqual(
        expect.objectContaining(propKeyValues)
    );
}
