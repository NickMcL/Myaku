/**
 * Mock MyakuWeb API response data for use in tests.
 * @module tests/testData
 */

import {
    SearchResources,
    SearchResultPage,
} from 'ts/types/types';

export const BASELINE_SEARCH_RESULT_PAGE: SearchResultPage = {
    search: {
        query: 'の',
        pageNum: 1,
    },
    totalResults: 21,
    hasNextPage: true,
    maxPageReached: false,
    results: [
        {
            articleId: 'id1',
            title: 'Article 1',
            sourceName: 'Source 1',
            sourceUrl: 'https://source1.com',
            publicationDatetime: new Date('2012-05-28T16:10:16Z'),
            lastUpdatedDatetime: new Date('2019-12-02T05:05:05Z'),
            instanceCount: 6,
            tags: ['Short length', 'Cool'],
            mainSampleText: {
                textStartPos: '50% into article',
                segments: [
                    {
                        isQueryMatch: false,
                        text: 'アメリカ',
                    },
                    {
                        isQueryMatch: true,
                        text: 'の',
                    },
                    {
                        isQueryMatch: false,
                        text: '一番',
                    },
                    {
                        isQueryMatch: true,
                        text: 'の',
                    },
                    {
                        isQueryMatch: false,
                        text: 'ネコ',
                    },
                ],
            },
            moreSampleTexts: [
                {
                    textStartPos: '30% into article',
                    segments: [
                        {
                            isQueryMatch: false,
                            text: 'アメリカ',
                        },
                        {
                            isQueryMatch: true,
                            text: 'の',
                        },
                        {
                            isQueryMatch: false,
                            text: '心',
                        },
                    ],
                },
                {
                    textStartPos: '80% into article',
                    segments: [
                        {
                            isQueryMatch: false,
                            text: 'アメリカ',
                        },
                        {
                            isQueryMatch: true,
                            text: 'の',
                        },
                        {
                            isQueryMatch: false,
                            text: '牛',
                        },
                    ],
                },
            ],
        },
        {
            articleId: 'id2',
            title: 'Article 2',
            sourceName: 'Source 2',
            sourceUrl: 'https://source2.com',
            publicationDatetime: new Date('2011-05-28T16:10:16Z'),
            lastUpdatedDatetime: null,
            instanceCount: 2,
            tags: ['Medium length'],
            mainSampleText: {
                textStartPos: '42% into article',
                segments: [
                    {
                        isQueryMatch: false,
                        text: 'アメリカ',
                    },
                    {
                        isQueryMatch: true,
                        text: 'の',
                    },
                    {
                        isQueryMatch: false,
                        text: '一番',
                    },
                ],
            },
            moreSampleTexts: [],
        },
    ],
};

export const SEARCH_RESOURCES_NO: SearchResources = {
    query: 'の',
    resourceLinkSets: [
        {
            setName: 'Jpn-Eng Dictionaries',
            resourceLinks: [
                {
                    resourceName: 'Jisho.org',
                    link: 'https://jisho.org/search/%E3%81%AE',
                },
                {
                    resourceName: 'Weblio EJJE',
                    link: 'https://ejje.weblio.jp/content/%E3%81%AE',
                },
            ],
        },
        {
            setName: 'Jpn-Eng Sample Sentences',
            resourceLinks: [
                {
                    resourceName: 'Tatoeba',
                    link: (
                        'https://tatoeba.org/eng/sentences/search?'
                        + 'query=%3D%E3%81%AE&from=jpn&to=eng'
                    ),
                },
                {
                    resourceName: 'Weblio EJJE',
                    link: (
                        'https://ejje.weblio.jp/sentence/content/'
                        + '%22%E3%81%AE%22'
                    ),
                },
            ],
        },
        {
            setName: 'Jpn Dictionaries',
            resourceLinks: [
                {
                    resourceName: 'Goo',
                    link: (
                        'https://dictionary.goo.ne.jp/srch/all/%E3%81%AE/m1u/'
                    ),
                },
                {
                    resourceName: 'Weblio',
                    link: 'https://www.weblio.jp/content/%E3%81%AE',
                },
            ],
        },
    ],
};

export const SEARCH_RESOURCES_OB: SearchResources = {
    query: 'OB',
    resourceLinkSets: [
        {
            setName: 'Jpn-Eng Dictionaries',
            resourceLinks: [
                {
                    resourceName: 'Jisho.org',
                    link: 'https://jisho.org/search/OB',
                },
                {
                    resourceName: 'Weblio EJJE',
                    link: 'https://ejje.weblio.jp/content/OB',
                },
            ],
        },
        {
            setName: 'Jpn-Eng Sample Sentences',
            resourceLinks: [
                {
                    resourceName: 'Tatoeba',
                    link: (
                        'https://tatoeba.org/eng/sentences/search?'
                        + 'query=%3DOB&from=jpn&to=eng'
                    ),
                },
                {
                    resourceName: 'Weblio EJJE',
                    link: 'https://ejje.weblio.jp/sentence/content/%22OB%22',
                },
            ],
        },
        {
            setName: 'Jpn Dictionaries',
            resourceLinks: [
                {
                    resourceName: 'Goo',
                    link: (
                        'https://dictionary.goo.ne.jp/srch/all/OB/m1u/'
                    ),
                },
                {
                    resourceName: 'Weblio',
                    link: 'https://www.weblio.jp/content/OB',
                },
            ],
        },
    ],
};

export function getSearchResultPageDataClone(): SearchResultPage {
    var clone = JSON.parse(
        JSON.stringify(BASELINE_SEARCH_RESULT_PAGE)
    ) as SearchResultPage;

    for (const result of clone.results) {
        result.publicationDatetime = new Date(result.publicationDatetime);
        if (result.lastUpdatedDatetime !== null) {
            result.lastUpdatedDatetime = new Date(result.lastUpdatedDatetime);
        }
    }
    return clone;
}
