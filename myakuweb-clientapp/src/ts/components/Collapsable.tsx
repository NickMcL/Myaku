/** @module Wrapper for a collapsable component */

import React from 'react';
import { reflow } from '../utils';

interface CollapsableProps {
    children: React.ReactNode;
    collapsed: boolean;
    onAnimationStart?: () => void;
    onAnimationEnd?: () => void;
}
type Props = CollapsableProps;

interface CollapsableState {
    collapsed: boolean;
    animationStarted: boolean;
}
type State = CollapsableState;

interface CollapsableStyle {
    height?: string;
}


class Collapsable extends React.Component<Props, State> {
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

    componentDidUpdate(): void {
        var collapsable = this._collapsableRef.current;
        if (
            this.state.animationStarted
            || collapsable === null
            || this.props.collapsed === this.state.collapsed
        ) {
            return;
        }

        reflow(collapsable);
        this.setState({
            animationStarted: true,
        });
        if (this.props.onAnimationStart) {
            this.props.onAnimationStart();
        }
    }

    bindEventHandlers(): void {
        this.handleAnimationEnd = this.handleAnimationEnd.bind(this);
    }

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

    getNoAnimationClassList(): string[] {
        if (this.props.collapsed) {
            return ['collapse'];
        } else {
            return ['collapse', 'show'];
        }
    }

    getAnimationClassList(): string[] {
        if (this.props.collapsed && !this.state.animationStarted) {
            return ['collapse', 'show'];
        } else {
            return ['collapsing'];
        }
    }

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
        if (this.props.collapsed === this.state.collapsed) {
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
