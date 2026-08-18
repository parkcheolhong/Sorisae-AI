(globalThis as typeof globalThis & { __DEV__?: boolean }).__DEV__ = true;

jest.mock('@react-native-async-storage/async-storage', () => ({
    __esModule: true,
    default: {
        getItem: jest.fn(),
        setItem: jest.fn(),
        removeItem: jest.fn(),
    },
}));

jest.mock('expo-file-system/legacy', () => ({
    FileSystemUploadType: { MULTIPART: 1, BINARY_CONTENT: 0 },
    cacheDirectory: 'file:///cache/',
    documentDirectory: 'file:///docs/',
    copyAsync: jest.fn(async () => undefined),
    uploadAsync: jest.fn(async () => ({ status: 200, body: '{}' })),
    getInfoAsync: jest.fn(async () => ({ exists: false })),
    readAsStringAsync: jest.fn(async () => ''),
    writeAsStringAsync: jest.fn(async () => undefined),
    deleteAsync: jest.fn(async () => undefined),
}));

jest.mock('expo-image-manipulator', () => ({
    manipulateAsync: jest.fn(async (uri: string) => ({ uri, width: 1, height: 1 })),
    SaveFormat: { JPEG: 'jpeg', PNG: 'png', WEBP: 'webp' },
}));

jest.mock('expo-constants', () => ({
    expoConfig: {
        extra: {
            apiBaseUrl: 'http://127.0.0.1:8000',
        },
    },
}));
