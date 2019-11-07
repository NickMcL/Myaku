module.exports = {
    moduleDirectories: [
        'node_modules',
        'src',
    ],
    moduleNameMapper: {
        '\\.svg$': '<rootDir>src/tests/__mocks__/fileMock.tsx',
    },
    roots: [
        '<rootDir>/src',
    ],
    transform: {
        '^.+\\.tsx?$': 'ts-jest',
    },
    setupFiles: [
        'fake-indexeddb/auto',
    ],
    setupFilesAfterEnv: [
        '<rootDir>/src/tests/setupTests.tsx',
    ],
    snapshotSerializers: [
        'enzyme-to-json/serializer',
    ],
};
