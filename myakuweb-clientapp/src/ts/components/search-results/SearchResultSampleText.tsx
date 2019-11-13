/**
 * SearchResultSampleText component module. See [[SearchResultSampleText]].
 */

import { ArticleSampleText } from 'ts/types/types';
import React from 'react';

/** Props for the [[SearchResultSampleText]] component. */
interface SearchResultSampleTextProps {
    /** Sample text content to display in the component */
    sampleText: ArticleSampleText;
}
type Props = SearchResultSampleTextProps;


/**
 * Article search result sample text blockquote component.
 *
 * @param props - See [[SearchResultSampleTextProps]].
 */
const SearchResultSampleText: React.FC<Props> = function(props) {
    var sampleSegments: React.ReactNode[] = [];
    var segments = props.sampleText.segments;
    for (let i = 0; i < segments.length; ++i) {
        if (segments[i].isQueryMatch) {
            sampleSegments.push(
                <span key={`segment-${i}`} className='article-sample-instance'>
                    {segments[i].text}
                </span>
            );
        } else {
            sampleSegments.push(segments[i].text);
        }
    }

    return (
        <blockquote className='article-sample-text'>
            <p lang='ja'>
                {sampleSegments}
            </p>
            <footer>
                {props.sampleText.textStartPos}
            </footer>
        </blockquote>
    );
};

export default SearchResultSampleText;
