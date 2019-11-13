/**
 * Collapsable component module. See [[Collapsable]].
 */

import React from 'react';
import { reflow } from 'ts/app/utils';

/** Props for the [[Collasable]] component. */
interface CollapsableProps {
    /** Child nodes to make collapsable. */
    children: React.ReactNode;

    /**
     * If true, the component will be collapsed (hiding the children), and
     * if false the component will be uncollapsed (showing the children).
     */
    collapsed: boolean;

    /**
     * If true, changes between collapsed and uncollapsed will be animated, and
     * if false, those changes will be instant with no animation.
     */
    animate: boolean;

    /**
     * Callback function that will be called whenever a collapse or uncollapse
     * animation starts.
     */
    onAnimationStart?: () => void;

    /**
     * Callback function that will be called whenever a collapse or uncollapse
     * animation ends.
     */
    onAnimationEnd?: () => void;
}
type Props = CollapsableProps;

/** State for the [[Collapsable]] component. */
interface CollapsableState {
    /**
     * Whether the collapsable is currently collapsed (true) or uncollapsed
     * (false).
     *
     * @remarks
     * The collapsed prop value indicates the current desired collapsed state,
     * but the collapsed state value indicates the actual current collapsed
     * state.
     * If these two values differ, the component will work to change its
     * collapse/uncollapse state (possibly with an animation depending on the
     * animate prop value) so that the state value will then match the prop
     * value.
     */
    collapsed: boolean;

    /**
     * Whether a collapse/uncollapse animation has started (true) or not
     * (false).
     */
    animationStarted: boolean;
}
type State = CollapsableState;

/** CSS style modified in the process of collapse/uncollapse animation */
interface CollapsableStyle {
    /**
     * The height must be explicitly set inline to trigger the animation at
     * times.
     */
    height?: string;
}


/**
 * Wrapper component to make another component collapsable.
 *
 * @remarks
 * See [[CollapsableProps]] and [[CollapsableState]] for props and state
 * details.
 */
class Collapsable extends React.Component<Props, State> {
    /** Ref for the collapsable container element. */
    private _collapsableRef: React.RefObject<HTMLDivElement>;

    constructor(props: Props) {
        super(props);
        this.bindEventHandlers();
        this._collapsableRef = React.createRef();

        this.state = {
            collapsed: this.props.collapsed,
            animationStarted: false,
        };
    }

    /**
     * Start the collapse/uncollapse animation if necessary.
     *
     * @remarks
     * If the collapsed prop and state values do not currently match and no
     * animation has been started, starts the collapse/uncollapse animation so
     * that the collapsed state value will match the prop value after the
     * animation.
     *
     * If the animate prop is false, just immediately sets the collapsed state
     * value to match the prop value.
     */
    componentDidUpdate(): void {
        var collapsable = this._collapsableRef.current;
        if (
            this.state.animationStarted
            || collapsable === null
            || this.props.collapsed === this.state.collapsed
        ) {
            return;
        }

        if (this.props.animate) {
            reflow(collapsable);
            this.setState({
                animationStarted: true,
            });
            if (this.props.onAnimationStart) {
                this.props.onAnimationStart();
            }
        } else {
            this.setState({
                collapsed: this.props.collapsed,
            });
        }
    }

    /**
     * Bind "this" for the event handlers used by the component.
     */
    bindEventHandlers(): void {
        this.handleAnimationEnd = this.handleAnimationEnd.bind(this);
    }

    /**
     * Callback for updating component state once a collapse/uncollapse
     * animation ends.
     */
    handleAnimationEnd(): void {
        if (this._collapsableRef.current !== null) {
            this._collapsableRef.current.removeEventListener(
                'transitionend', this.handleAnimationEnd
            );
        }
        this.setState({
            collapsed: this.props.collapsed,
            animationStarted: false,
        });
        if (this.props.onAnimationEnd) {
            this.props.onAnimationEnd();
        }
    }

    /**
     * Get the no-animation class list for the collapsable element based on the
     * current props.
     *
     * @returns The list of classes.
     */
    getNoAnimationClassList(): string[] {
        if (this.props.collapsed) {
            return ['collapse'];
        } else {
            return ['collapse', 'show'];
        }
    }

    /**
     * Get the animation class list for the collapsable element based on the
     * current props and state.
     *
     * @returns The list of classes.
     */
    getAnimationClassList(): string[] {
        if (this.props.collapsed && !this.state.animationStarted) {
            return ['collapse', 'show'];
        } else {
            return ['collapsing'];
        }
    }

    /**
     * Get the inline CSS style for the collapsable element based on the
     * current props and state.
     *
     * @returns The inline CSS styles.
     */
    getAnimationInlineStyle(): CollapsableStyle {
        var collapsable = this._collapsableRef.current;
        if (collapsable === null) {
            return {};
        }

        if (!this.props.collapsed) {
            return {
                height: collapsable.scrollHeight + 'px',
            };
        } else if (!this.state.animationStarted) {
            return {
                height: collapsable.getBoundingClientRect()['height'] + 'px',
            };
        } else {
            return {};
        }
    }

    /**
     * Set a callback to be called on a collapse/uncollapse animation end to
     * update component state.
     */
    addAnimationEndListener(): void {
        var collapsable = this._collapsableRef.current;
        if (collapsable === null) {
            return;
        }

        collapsable.addEventListener(
            'transitionend', this.handleAnimationEnd
        );
    }

    render(): React.ReactElement {
        var classList: string[] = [];
        var style: CollapsableStyle = {};
        if (
            this.props.collapsed === this.state.collapsed
            || !this.props.animate
        ) {
            classList = this.getNoAnimationClassList();
        } else {
            classList = this.getAnimationClassList();
            style = this.getAnimationInlineStyle();
            if (!this.state.animationStarted) {
                this.addAnimationEndListener();
            }
        }

        return (
            <div
                className={classList.join(' ')}
                style={style}
                ref={this._collapsableRef}
            >
                {this.props.children}
            </div>
        );
    }
}

export default Collapsable;
