/** @module Search result article sample text component */

import { ArticleSampleText } from '../types';
import React from 'react';

interface SearchResultSampleTextProps {
    sampleText: ArticleSampleText;
}
type Props = SearchResultSampleTextProps;


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
            <p className='japanese-text' lang='ja'>
                {sampleSegments}
            </p>
            <footer>
                {props.sampleText.textStartPos}
            </footer>
        </blockquote>
    );
};

export default SearchResultSampleText;
