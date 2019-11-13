/**
 * Utility functions for use in React component Jest tests.
 */

import {
    ComponentType,
    ReactWrapper,
    ShallowWrapper,
} from 'enzyme';


/**
 * Check for the presence of the given component in the given enzyme wrapper.
 *
 * Uses the expect function from Jest to make the checks, so this function can
 * only be called in Jest tests.
 *
 * @param wrapper - Enzyme wrapper to check for the component.
 * @param component - Component to check for.
 * @param propKeyValues - The values that each prop key should have for the
 * component in the wrapper.
 */
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
