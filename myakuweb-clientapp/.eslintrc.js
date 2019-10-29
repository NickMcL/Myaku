module.exports = {
    'env': {
        'browser': true,
        'es2017': true,
        'commonjs': true,
    },
    'extends': [
        'eslint:recommended',
        'plugin:react/recommended',
        'plugin:jsx-a11y/strict',
        'plugin:@typescript-eslint/eslint-recommended',
        'plugin:@typescript-eslint/recommended',
        'plugin:@typescript-eslint/recommended-requiring-type-checking',
    ],
    'globals': {
        'Atomics': 'readonly',
        'SharedArrayBuffer': 'readonly',
    },
    'parser': '@typescript-eslint/parser',
    'parserOptions': {
        'ecmaFeatures': {
            'jsx': true,
        },
        'sourceType': 'module',
        'project': './tsconfig.json',
    },
    'plugins': [
        'react',
        'react-hooks',
        'jsx-a11y',
        '@typescript-eslint',
    ],
    'settings': {
        'react': {
            'version': '16.10.2',
        },
    },
    'rules': {
        // ESLint rules
        'array-bracket-newline': [
            'error',
            'consistent',
        ],
        'array-bracket-spacing': [
            'error',
            'never',
        ],
        'arrow-spacing': 'error',
        'block-spacing': [
            'error',
            'always',
        ],
        'brace-style': 'off',  // Handled by TS rule
        'camelcase': 'off',  // Handled by TS rule
        'comma-dangle': [
            'error',
            {
                'arrays': 'always-multiline',
                'objects': 'always-multiline',
                'imports': 'always-multiline',
                'exports': 'always-multiline',
                'functions': 'never',
            },
        ],
        'comma-spacing': 'error',
        'comma-style': 'error',
        'computed-property-spacing': [
            'error',
            'never',
            {
                'enforceForClassMembers': true,
            },
        ],
        'curly': [
            'error',
            'all',
        ],
        'dot-location': [
            'error',
            'property',
        ],
        'func-call-spacing': 'off',  // Handled by TS rule
        'generator-star-spacing': [
            'error',
            'before',
        ],
        'indent': 'off',  // Handled by TS rule
        'jsx-quotes': [
            'error',
            'prefer-single',
        ],
        'key-spacing': 'error',
        'keyword-spacing': 'error',
        'linebreak-style': [
            'error',
            'unix',
        ],
        'lines-between-class-members': [
            'error',
            'always',
            {
                'exceptAfterSingleLine': true,
            },
        ],
        'max-len': [
            'error',
            {
                'code': 79,
                'tabWidth': 4,
                'ignoreUrls': true,
            },
        ],
        'max-lines-per-function': [
            'error',
            50,
        ],
        'new-parens': 'error',
        'no-alert': 'error',
        'no-empty-function': 'off',  // Handled by TS rule
        'no-floating-decimal': 'error',
        'no-lonely-if': 'error',
        'no-multiple-empty-lines': [
            'error',
            {
                'max': 2,
                'maxEOF': 0,
                'maxBOF': 1,
            },
        ],
        'no-multi-spaces': [
            'error',
            {
                'ignoreEOLComments': true,
            },
        ],
        'no-nested-ternary': 'error',
        'no-return-assign': [
            'error',
            'always',
        ],
        'no-tabs': 'error',
        'no-trailing-spaces': 'error',
        'no-unneeded-ternary': 'error',
        'no-unused-expressions': 'error',
        'no-use-before-define': 'off',  // Handled by TS rule
        'no-useless-computed-key': 'error',
        'no-var': 'off',
        'no-whitespace-before-property': 'error',
        'object-curly-newline': 'error',
        'operator-linebreak': [
            'error',
            'before',
        ],
        'padded-blocks': [
            'error',
            'never',
        ],
        'quotes': 'off',  // Handled by TS rule
        'require-await': 'off',  // Handled by TS rule
        'rest-spread-spacing': 'error',
        'semi': 'off',  // Handled by TS rule
        'semi-spacing': 'error',
        'semi-style': 'error',
        'sort-imports': [
            'error',
            {
                'memberSyntaxSortOrder': ['none', 'single', 'all', 'multiple'],
            },
        ],
        'space-before-blocks': 'error',
        'space-before-function-paren': [
            'error',
            'never',
        ],
        'space-in-parens': 'error',
        'space-infix-ops': 'error',
        'space-unary-ops': [
            'error',
            {
                'words': true,
                'nonwords': false,
            },
        ],
        'spaced-comment': 'error',
        'switch-colon-spacing': 'error',
        'yield-star-spacing': [
            'error',
            'before',
        ],
        'yoda': 'error',

        // React rules
        'react/button-has-type': 'error',
        'react/no-access-state-in-setstate': 'error',
        'react/no-array-index-key': 'error',
        'react/no-did-mount-set-state': 'off',
        'react/no-did-update-set-state': 'off',
        'react/no-redundant-should-component-update': 'error',
        'react/no-typos': 'error',
        'react/no-unused-state': 'off',
        'react/prefer-es6-class': 'error',
        'react/prefer-stateless-function': 'error',
        'react/prop-types': 'off',
        'react/sort-comp': [
            'error',
            {
                'order': [
                    'static-variables',
                    'instance-variables',
                    'static-methods',
                    'lifecycle',
                    '/^bindEventHandlers.*$/',
                    'everything-else',
                    'render',
                ],
            },
        ],
        'react/state-in-constructor': 'error',
        'react/static-property-placement': 'error',
        'react/style-prop-object': 'error',
        'react/void-dom-elements-no-children': 'error',

        // React hooks rules
        'react-hooks/rules-of-hooks': 'error',
        'react-hooks/exhaustive-deps': 'error',

        // React JSX rules
        'react/jsx-boolean-value': 'error',
        'react/jsx-closing-bracket-location': 'error',
        'react/jsx-closing-tag-location': 'error',
        'react/jsx-curly-newline': 'error',
        'react/jsx-curly-spacing': 'error',
        'react/jsx-equals-spacing': 'error',
        'react/jsx-filename-extension': [
            'error',
            {
                'extensions': ['.jsx', '.tsx'],
            },
        ],
        'react/jsx-first-prop-new-line': [
            'error',
            'multiline',
        ],
        'react/jsx-handler-names': 'error',
        'react/jsx-indent': [
            'error',
            4,
            {
                'checkAttributes': false,
                'indentLogicalExpressions': true,
            },
        ],
        'react/jsx-indent-props': [
            'error',
            4,
        ],
        'react/jsx-key': 'error',
        'react/jsx-no-bind': 'off',
        'react/jsx-no-useless-fragment': 'error',
        'react/jsx-fragments': [
            'error',
            'element',
        ],
        'react/jsx-pascal-case': 'error',
        'react/jsx-props-no-multi-spaces': 'error',
        'react/jsx-props-no-spreading': 'error',
        'react/jsx-tag-spacing': [
            'error',
            {
                'closingSlash': 'never',
                'beforeSelfClosing': 'always',
                'afterOpening': 'never',
                'beforeClosing': 'never',
            },
        ],
        'react/jsx-wrap-multilines': [
            'error',
            {
                'declaration': 'parens-new-line',
                'assignment': 'parens-new-line',
                'return': 'parens-new-line',
                'arrow': 'parens-new-line',
                'condition': 'parens-new-line',
                'logical': 'parens-new-line',
                'prop': 'parens-new-line'
            },
        ],

        // JSX a11y rules
        'jsx-a11y/label-has-associated-control': [
            'error',
            {
                'assert': 'either',
            },
        ],
        'jsx-a11y/label-has-for': [
            'error',
            {
                'required': 'id',
            },
        ],

        // Typescript rules
        '@typescript-eslint/adjacent-overload-signatures': 'error',
        '@typescript-eslint/array-type': [
            'error',
            {
                'default': 'array-simple',
            },
        ],
        '@typescript-eslint/await-thenable': 'error',
        '@typescript-eslint/ban-ts-ignore': 'error',
        '@typescript-eslint/ban-types': 'error',
        '@typescript-eslint/brace-style': [
            'error',
            '1tbs',
        ],
        '@typescript-eslint/camelcase': 'error',
        '@typescript-eslint/class-name-casing': 'error',
        '@typescript-eslint/consistent-type-assertions': 'error',
        '@typescript-eslint/consistent-type-definitions': [
            'error',
            'interface',
        ],
        '@typescript-eslint/explicit-function-return-type': 'error',
        '@typescript-eslint/func-call-spacing': 'error',
        '@typescript-eslint/indent': [
            'error',
            4,
            {
                'ignoredNodes': [
                    'TSParenthesizedType',
                    'TSTypeParameterInstantiation',
                ],
            },
        ],
        '@typescript-eslint/interface-name-prefix': 'error',
        '@typescript-eslint/member-delimiter-style': 'error',
        '@typescript-eslint/member-naming': [
            'error',
            {
                'private': '^_',
            },
        ],
        '@typescript-eslint/member-ordering': 'error',
        '@typescript-eslint/no-array-constructor': 'error',
        '@typescript-eslint/no-empty-function': 'error',
        '@typescript-eslint/no-empty-interface': 'error',
        '@typescript-eslint/no-explicit-any': 'error',
        '@typescript-eslint/no-floating-promises': 'off',
        '@typescript-eslint/no-for-in-array': 'error',
        '@typescript-eslint/no-inferrable-types': 'error',
        '@typescript-eslint/no-misused-new': 'error',
        '@typescript-eslint/no-misused-promises': 'error',
        '@typescript-eslint/no-namespace': 'error',
        '@typescript-eslint/no-non-null-assertion': 'error',
        '@typescript-eslint/no-this-alias': 'error',
        '@typescript-eslint/no-unnecessary-condition': [
            'error',
            {
                'ignoreRhs': true,
            },
        ],
        '@typescript-eslint/no-unnecessary-type-assertion': 'error',
        '@typescript-eslint/no-unused-vars': 'error',
        '@typescript-eslint/no-use-before-define': 'error',
        '@typescript-eslint/no-var-requires': 'error',
        '@typescript-eslint/prefer-for-of': 'error',
        '@typescript-eslint/prefer-includes': 'error',
        '@typescript-eslint/prefer-namespace-keyword': 'error',
        '@typescript-eslint/prefer-regexp-exec': 'error',
        '@typescript-eslint/prefer-string-starts-ends-with': 'error',
        '@typescript-eslint/promise-function-async': 'error',
        '@typescript-eslint/quotes': [
            'error',
            'single',
        ],
        '@typescript-eslint/require-array-sort-compare': 'error',
        '@typescript-eslint/require-await': 'off',
        '@typescript-eslint/semi': [
            'error',
            'always',
        ],
        '@typescript-eslint/triple-slash-reference': 'error',
        '@typescript-eslint/type-annotation-spacing': 'error',
        '@typescript-eslint/unbound-method': 'off',
        '@typescript-eslint/unified-signatures': 'error',
    },
    'overrides': [
        {
            'files': ['*.js'],
            'parser': 'espree',
            'parserOptions': {
                'emcaVersion': 2019,
            },
            'env': {
                'es2017': true,
                'commonjs': true,
                'node': true,
            },
            'plugins': [],
            'extends': [
                'eslint:recommended',
            ],
            'rules': {
                // Re-enable rules superceded by Typescript rules
                'brace-style': [
                    'error',
                    '1tbs',
                ],
                'camelcase': 'error',
                'func-call-spacing': 'error',
                'indent': [
                    'error',
                    4,
                ],
                'no-empty-function': 'error',
                'no-use-before-define': 'error',
                'quotes': [
                    'error',
                    'single',
                ],
                'require-await': 'error',
                'semi': [
                    'error',
                    'always',
                ],

                // Turn off all Typescript rules
                '@typescript-eslint/adjacent-overload-signatures': 'off',
                '@typescript-eslint/array-type': 'off',
                '@typescript-eslint/await-thenable': 'off',
                '@typescript-eslint/ban-ts-ignore': 'off',
                '@typescript-eslint/ban-types': 'off',
                '@typescript-eslint/brace-style': 'off',
                '@typescript-eslint/camelcase': 'off',
                '@typescript-eslint/class-name-casing': 'off',
                '@typescript-eslint/consistent-type-assertions': 'off',
                '@typescript-eslint/consistent-type-definitions': 'off',
                '@typescript-eslint/explicit-function-return-type': 'off',
                '@typescript-eslint/func-call-spacing': 'off',
                '@typescript-eslint/indent': 'off',
                '@typescript-eslint/interface-name-prefix': 'off',
                '@typescript-eslint/member-delimiter-style': 'off',
                '@typescript-eslint/member-naming': 'off',
                '@typescript-eslint/member-ordering': 'off',
                '@typescript-eslint/no-array-constructor': 'off',
                '@typescript-eslint/no-empty-function': 'off',
                '@typescript-eslint/no-empty-interface': 'off',
                '@typescript-eslint/no-explicit-any': 'off',
                '@typescript-eslint/no-floating-promises': 'off',
                '@typescript-eslint/no-for-in-array': 'off',
                '@typescript-eslint/no-inferrable-types': 'off',
                '@typescript-eslint/no-misused-new': 'off',
                '@typescript-eslint/no-misused-promises': 'off',
                '@typescript-eslint/no-namespace': 'off',
                '@typescript-eslint/no-non-null-assertion': 'off',
                '@typescript-eslint/no-this-alias': 'off',
                '@typescript-eslint/no-unnecessary-condition': 'off',
                '@typescript-eslint/no-unnecessary-type-assertion': 'off',
                '@typescript-eslint/no-unused-vars': 'off',
                '@typescript-eslint/no-use-before-define': 'off',
                '@typescript-eslint/no-var-requires': 'off',
                '@typescript-eslint/prefer-for-of': 'off',
                '@typescript-eslint/prefer-includes': 'off',
                '@typescript-eslint/prefer-namespace-keyword': 'off',
                '@typescript-eslint/prefer-regexp-exec': 'off',
                '@typescript-eslint/prefer-string-starts-ends-with': 'off',
                '@typescript-eslint/promise-function-async': 'off',
                '@typescript-eslint/quotes': 'off',
                '@typescript-eslint/require-array-sort-compare': 'off',
                '@typescript-eslint/require-await': 'off',
                '@typescript-eslint/semi': 'off',
                '@typescript-eslint/triple-slash-reference': 'off',
                '@typescript-eslint/type-annotation-spacing': 'off',
                '@typescript-eslint/unbound-method': 'off',
                '@typescript-eslint/unified-signatures': 'off',
            },
        },
    ],
};
