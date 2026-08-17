import Constants from 'expo-constants';
import * as FileSystem from 'expo-file-system';
import * as SecureStore from 'expo-secure-store';
import * as Sharing from 'expo-sharing';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useMemo, useState } from 'react';
import {
    ActivityIndicator,
    Switch,
    Pressable,
    SafeAreaView,
    ScrollView,
    StyleSheet,
    Text,
    TextInput,
    View,
} from 'react-native';
import { getDetectorStatus, getLatestApkUrl, getMarketplaceSummary, postVoiceOrchestrate } from './src/api';

type ScreenKey = 'auth' | 'order' | 'download';
type OrderConfirmState = 'idle' | 'prepared';

function resolveMaxStopLossPercent(): number {
    const raw = (Constants.expoConfig?.extra?.maxStopLossPercent as number | string | undefined) ?? 2;
    const parsed = Number(raw);
    return Number.isFinite(parsed) && parsed > 0 ? parsed : 2;
}

const MAX_STOP_LOSS_PERCENT = resolveMaxStopLossPercent();

const STORE_KEYS = {
    apiBaseUrl: 'mobile_stock_ai_api_base_url',
    token: 'mobile_stock_ai_token',
    tokenHeaderName: 'mobile_stock_ai_token_header_name',
};

function pretty(value: unknown): string {
    try {
        return JSON.stringify(value, null, 2);
    } catch {
        return String(value);
    }
}

const defaultBaseUrl =
    (Constants.expoConfig?.extra?.apiBaseUrl as string | undefined) ||
    'http://10.0.2.2:3010';

export default function App() {
    const [screen, setScreen] = useState<ScreenKey>('auth');
    const [orderConfirmState, setOrderConfirmState] = useState<OrderConfirmState>('idle');
    const [baseUrl, setBaseUrl] = useState(defaultBaseUrl);
    const [token, setToken] = useState('');
    const [tokenHeaderName, setTokenHeaderName] = useState('Authorization');
    const [task, setTask] = useState('stock signal summary for today');
    const [agentKey, setAgentKey] = useState('reasoner');
    const [riskPercent, setRiskPercent] = useState('1.0');
    const [orderQty, setOrderQty] = useState('1');
    const [stopLossPercent, setStopLossPercent] = useState('0.7');
    const [isFinalConfirmed, setIsFinalConfirmed] = useState(false);
    const [autoApply, setAutoApply] = useState(false);
    const [isBusy, setIsBusy] = useState(false);
    const [result, setResult] = useState('Press a button to call API');
    const [errorText, setErrorText] = useState('');

    const normalizedBaseUrl = useMemo(() => baseUrl.trim().replace(/\/$/, ''), [baseUrl]);
    const authConfig = useMemo(() => ({ token, tokenHeaderName }), [token, tokenHeaderName]);

    const parsedRisk = Number(riskPercent);
    const parsedQty = Number(orderQty);
    const parsedStopLoss = Number(stopLossPercent);
    const orderReady = Number.isFinite(parsedRisk) && parsedRisk > 0 && Number.isFinite(parsedQty) && parsedQty > 0 && Number.isFinite(parsedStopLoss) && parsedStopLoss > 0;

    useEffect(() => {
        const loadSecureConfig = async () => {
            try {
                const [storedBaseUrl, storedToken, storedTokenHeaderName] = await Promise.all([
                    SecureStore.getItemAsync(STORE_KEYS.apiBaseUrl),
                    SecureStore.getItemAsync(STORE_KEYS.token),
                    SecureStore.getItemAsync(STORE_KEYS.tokenHeaderName),
                ]);

                if (storedBaseUrl) {
                    setBaseUrl(storedBaseUrl);
                }
                if (storedToken) {
                    setToken(storedToken);
                }
                if (storedTokenHeaderName) {
                    setTokenHeaderName(storedTokenHeaderName);
                }
            } catch (error) {
                setErrorText(error instanceof Error ? error.message : String(error));
            }
        };

        loadSecureConfig();
    }, []);

    const saveSecureConfig = async () => {
        try {
            await Promise.all([
                SecureStore.setItemAsync(STORE_KEYS.apiBaseUrl, normalizedBaseUrl),
                SecureStore.setItemAsync(STORE_KEYS.token, token),
                SecureStore.setItemAsync(STORE_KEYS.tokenHeaderName, tokenHeaderName),
            ]);
            setResult('Auth/API configuration saved securely.');
            setErrorText('');
        } catch (error) {
            setErrorText(error instanceof Error ? error.message : String(error));
        }
    };

    const runAction = async (action: () => Promise<unknown>) => {
        setIsBusy(true);
        setErrorText('');
        try {
            const data = await action();
            setResult(pretty(data));
        } catch (error) {
            const message = error instanceof Error ? error.message : String(error);
            setErrorText(message);
        } finally {
            setIsBusy(false);
        }
    };

    const handlePrepareOrder = () => {
        if (!orderReady) {
            setErrorText('리스크/수량/손절 값은 0보다 큰 숫자여야 합니다.');
            return;
        }

        if (parsedStopLoss > MAX_STOP_LOSS_PERCENT) {
            setOrderConfirmState('idle');
            setIsFinalConfirmed(false);
            setErrorText(`손절 하드게이트 초과: ${MAX_STOP_LOSS_PERCENT}% 이하여야 합니다.`);
            return;
        }

        setOrderConfirmState('prepared');
        setIsFinalConfirmed(false);
        setErrorText('');
        setResult(
            pretty({
                step: 'prepared',
                riskPercent: parsedRisk,
                orderQty: parsedQty,
                stopLossPercent: parsedStopLoss,
                note: '2단계 확인을 진행한 뒤 최종 주문을 실행하세요.',
            }),
        );
    };

    const handleExecuteOrder = async () => {
        if (orderConfirmState !== 'prepared') {
            setErrorText('먼저 1단계 준비 검증을 완료하세요.');
            return;
        }
        if (parsedStopLoss > MAX_STOP_LOSS_PERCENT) {
            setOrderConfirmState('idle');
            setIsFinalConfirmed(false);
            setErrorText(`손절 하드게이트 초과: ${MAX_STOP_LOSS_PERCENT}% 이하여야 합니다.`);
            return;
        }
        if (!isFinalConfirmed) {
            setErrorText('2단계 최종 확인 스위치를 켜주세요.');
            return;
        }

        const enrichedTask = [
            task,
            `[risk=${parsedRisk}%]`,
            `[qty=${parsedQty}]`,
            `[stop_loss=${parsedStopLoss}%]`,
        ].join(' ');

        await runAction(() =>
            postVoiceOrchestrate(
                normalizedBaseUrl,
                {
                    transcript: enrichedTask,
                    task: enrichedTask,
                    tts: false,
                    auto_apply: autoApply,
                    agent_key: agentKey,
                    run_id: null,
                    output_dir: null,
                    conversation: [
                        {
                            type: 'risk_guard',
                            riskPercent: parsedRisk,
                            quantity: parsedQty,
                            stopLossPercent: parsedStopLoss,
                            confirmed: true,
                        },
                    ],
                },
                authConfig,
            ),
        );
    };

    return (
        <SafeAreaView style={styles.safe}>
            <StatusBar style="light" />
            <ScrollView contentContainerStyle={styles.container}>
                <Text style={styles.title}>Stock AI Native App</Text>
                <Text style={styles.subtitle}>iOS / Android API Client</Text>

                <View style={styles.card}>
                    <Text style={styles.label}>API Base URL</Text>
                    <TextInput
                        style={styles.input}
                        value={baseUrl}
                        onChangeText={setBaseUrl}
                        autoCapitalize="none"
                        autoCorrect={false}
                        placeholder="http://10.0.2.2:3010"
                        placeholderTextColor="#6b7280"
                    />
                    <Text style={styles.helper}>
                        Android emulator: 10.0.2.2, iOS simulator: 127.0.0.1, physical device: PC LAN IP
                    </Text>
                </View>

                <View style={styles.card}>
                    <Text style={styles.label}>Task Prompt</Text>
                    <TextInput
                        style={styles.input}
                        value={task}
                        onChangeText={setTask}
                        autoCapitalize="none"
                        autoCorrect={false}
                    />

                    <Text style={styles.label}>Agent Key</Text>
                    <TextInput
                        style={styles.input}
                        value={agentKey}
                        onChangeText={setAgentKey}
                        autoCapitalize="none"
                        autoCorrect={false}
                    />
                </View>

                <View style={styles.row}>
                    <Pressable
                        style={styles.button}
                        disabled={isBusy}
                        onPress={() => runAction(() => getMarketplaceSummary(normalizedBaseUrl))}
                    >
                        <Text style={styles.buttonText}>Metrics Summary</Text>
                    </Pressable>

                    <Pressable
                        style={styles.button}
                        disabled={isBusy}
                        onPress={() => runAction(() => getDetectorStatus(normalizedBaseUrl))}
                    >
                        <Text style={styles.buttonText}>Detector Status</Text>
                    </Pressable>
                </View>

                <Pressable
                    style={[styles.button, styles.primary]}
                    disabled={isBusy}
                    onPress={() =>
                        runAction(() =>
                            postVoiceOrchestrate(normalizedBaseUrl, {
                                transcript: task,
                                task,
                                tts: false,
                                auto_apply: false,
                                agent_key: agentKey,
                                run_id: null,
                                output_dir: null,
                                conversation: [],
                            }),
                        )
                    }
                >
                    <Text style={styles.buttonText}>Run Orchestrate</Text>
                </Pressable>

                {isBusy && <ActivityIndicator color="#22c55e" style={styles.loader} />}

                {errorText ? (
                    <View style={styles.errorBox}>
                        <Text style={styles.errorTitle}>Error</Text>
                        <Text style={styles.errorText}>{errorText}</Text>
                    </View>
                ) : null}

                <View style={styles.tabRow}>
                    <Pressable style={[styles.tabButton, screen === 'auth' ? styles.tabButtonActive : null]} onPress={() => setScreen('auth')}>
                        <Text style={styles.tabText}>인증</Text>
                    </Pressable>
                    <Pressable style={[styles.tabButton, screen === 'order' ? styles.tabButtonActive : null]} onPress={() => setScreen('order')}>
                        <Text style={styles.tabText}>주문</Text>
                    </Pressable>
                    <Pressable style={[styles.tabButton, screen === 'download' ? styles.tabButtonActive : null]} onPress={() => setScreen('download')}>
                        <Text style={styles.tabText}>다운로드</Text>
                    </Pressable>
                </View>

                {screen === 'auth' ? (
                    <View style={styles.card}>
                        <Text style={styles.label}>API Base URL</Text>
                        <TextInput
                            style={styles.input}
                            value={baseUrl}
                            onChangeText={setBaseUrl}
                            autoCapitalize="none"
                            autoCorrect={false}
                            placeholder="http://10.0.2.2:3010"
                            placeholderTextColor="#6b7280"
                        />

                        <Text style={styles.label}>Token Header Name</Text>
                        <TextInput
                            style={styles.input}
                            value={tokenHeaderName}
                            onChangeText={setTokenHeaderName}
                            autoCapitalize="none"
                            autoCorrect={false}
                            placeholder="Authorization"
                            placeholderTextColor="#6b7280"
                        />

                        <Text style={styles.label}>Access Token</Text>
                        <TextInput
                            style={styles.input}
                            value={token}
                            onChangeText={setToken}
                            secureTextEntry
                            autoCapitalize="none"
                            autoCorrect={false}
                            placeholder="Bearer token or raw token"
                            placeholderTextColor="#6b7280"
                        />

                        <Text style={styles.helper}>
                            Header name이 Authorization면 자동으로 Bearer 접두사를 붙입니다.
                        </Text>

                        <View style={styles.row}>
                            <Pressable style={styles.button} disabled={isBusy} onPress={saveSecureConfig}>
                                <Text style={styles.buttonText}>저장</Text>
                            </Pressable>
                            <Pressable
                                style={styles.button}
                                disabled={isBusy}
                                onPress={() => runAction(() => getMarketplaceSummary(normalizedBaseUrl, authConfig))}
                            >
                                <Text style={styles.buttonText}>인증 테스트</Text>
                            </Pressable>
                        </View>
                    </View>
                ) : null}

                {screen === 'order' ? (
                    <View style={styles.card}>
                        <Text style={styles.sectionTitle}>1단계: 주문 조건 입력</Text>

                        <Text style={styles.label}>Task Prompt</Text>
                        <TextInput
                            style={styles.input}
                            value={task}
                            onChangeText={setTask}
                            autoCapitalize="none"
                            autoCorrect={false}
                        />

                        <Text style={styles.label}>Agent Key</Text>
                        <TextInput
                            style={styles.input}
                            value={agentKey}
                            onChangeText={setAgentKey}
                            autoCapitalize="none"
                            autoCorrect={false}
                        />

                        <Text style={styles.label}>리스크 비율 (%)</Text>
                        <TextInput
                            style={styles.input}
                            value={riskPercent}
                            onChangeText={setRiskPercent}
                            keyboardType="decimal-pad"
                            autoCapitalize="none"
                            autoCorrect={false}
                        />

                        <Text style={styles.label}>주문 수량</Text>
                        <TextInput
                            style={styles.input}
                            value={orderQty}
                            onChangeText={setOrderQty}
                            keyboardType="number-pad"
                            autoCapitalize="none"
                            autoCorrect={false}
                        />

                        <Text style={styles.label}>손절 비율 (%)</Text>
                        <TextInput
                            style={styles.input}
                            value={stopLossPercent}
                            onChangeText={setStopLossPercent}
                            keyboardType="decimal-pad"
                            autoCapitalize="none"
                            autoCorrect={false}
                        />
                        <Text style={styles.helper}>하드게이트: 손절은 최대 {MAX_STOP_LOSS_PERCENT}%</Text>

                        <View style={styles.row}>
                            <Pressable
                                style={[styles.button, autoApply ? styles.primary : null]}
                                disabled={isBusy}
                                onPress={() => setAutoApply((v) => !v)}
                            >
                                <Text style={styles.buttonText}>{autoApply ? 'Auto Apply: ON' : 'Auto Apply: OFF'}</Text>
                            </Pressable>
                            <Pressable style={styles.button} disabled={isBusy} onPress={handlePrepareOrder}>
                                <Text style={styles.buttonText}>1단계 검증</Text>
                            </Pressable>
                        </View>

                        {orderConfirmState === 'prepared' ? (
                            <View style={styles.confirmPanel}>
                                <Text style={styles.sectionTitle}>2단계: 최종 확인</Text>
                                <Text style={styles.helper}>리스크 {parsedRisk}% · 수량 {parsedQty} · 손절 {parsedStopLoss}%</Text>
                                <View style={styles.switchRow}>
                                    <Text style={styles.switchLabel}>실주문 전 최종 확인</Text>
                                    <Switch value={isFinalConfirmed} onValueChange={setIsFinalConfirmed} />
                                </View>
                            </View>
                        ) : null}

                        <View style={styles.row}>
                            <Pressable
                                style={styles.button}
                                disabled={isBusy}
                                onPress={() => runAction(() => getDetectorStatus(normalizedBaseUrl, authConfig))}
                            >
                                <Text style={styles.buttonText}>상태 조회</Text>
                            </Pressable>
                            <Pressable
                                style={[styles.button, styles.primary]}
                                disabled={isBusy || !isFinalConfirmed || orderConfirmState !== 'prepared'}
                                onPress={handleExecuteOrder}
                            >
                                <Text style={styles.buttonText}>2단계 최종 주문</Text>
                            </Pressable>
                        </View>
                    </View>
                ) : null}

                {screen === 'download' ? (
                    <View style={styles.card}>
                        <Text style={styles.label}>자동 업데이트 APK</Text>
                        <Text style={styles.helper}>
                            고정 경로: /api/marketplace/latest.apk
                        </Text>
                        <Text style={styles.helper}>
                            tar.gz/pdf 응답은 자동 차단하고, .apk만 다운로드합니다.
                        </Text>

                        <View style={styles.row}>
                            <Pressable
                                style={[styles.button, styles.primary]}
                                disabled={isBusy}
                                onPress={() =>
                                    runAction(async () => {
                                        const url = getLatestApkUrl(normalizedBaseUrl);
                                        const destination = `${FileSystem.cacheDirectory || FileSystem.documentDirectory}stock-ai-latest-${Date.now()}.apk`;
                                        const headers: Record<string, string> = {};

                                        if (token.trim()) {
                                            if (tokenHeaderName.trim().toLowerCase() === 'authorization') {
                                                headers.Authorization = token.toLowerCase().startsWith('bearer ')
                                                    ? token
                                                    : `Bearer ${token}`;
                                            } else {
                                                headers[tokenHeaderName.trim() || 'Authorization'] = token;
                                            }
                                        }

                                        let headerContentType = '';
                                        let headerDisposition = '';
                                        try {
                                            const headResponse = await fetch(url, {
                                                method: 'HEAD',
                                                headers,
                                            });
                                            if (headResponse.ok) {
                                                headerContentType = (headResponse.headers.get('content-type') || '').toLowerCase();
                                                headerDisposition = (headResponse.headers.get('content-disposition') || '').toLowerCase();
                                            }
                                        } catch {
                                            // Some gateways may block HEAD; enforce type after download as a fallback.
                                        }

                                        if (
                                            headerContentType.includes('application/pdf') ||
                                            headerContentType.includes('application/zip') ||
                                            headerContentType.includes('application/gzip') ||
                                            headerContentType.includes('application/x-gzip') ||
                                            headerContentType.includes('application/x-tar') ||
                                            headerContentType.includes('application/octet-stream+tar')
                                        ) {
                                            throw new Error(`업데이트 차단: APK가 아닌 응답 타입(${headerContentType})입니다.`);
                                        }

                                        const downloadResult = await FileSystem.downloadAsync(url, destination, { headers });
                                        const downloadHeaders = (downloadResult as unknown as { headers?: Record<string, string> }).headers || {};
                                        const downloadedType = (
                                            downloadHeaders['content-type'] ||
                                            downloadHeaders['Content-Type'] ||
                                            headerContentType ||
                                            ''
                                        ).toLowerCase();
                                        const downloadedDisposition = (
                                            downloadHeaders['content-disposition'] ||
                                            downloadHeaders['Content-Disposition'] ||
                                            headerDisposition ||
                                            ''
                                        ).toLowerCase();

                                        const isApkByType = downloadedType.includes('application/vnd.android.package-archive');
                                        const isApkByDisposition = downloadedDisposition.includes('.apk');
                                        const isApkByPath = downloadResult.uri.toLowerCase().endsWith('.apk');
                                        const isBlockedType =
                                            downloadedType.includes('application/pdf') ||
                                            downloadedType.includes('application/zip') ||
                                            downloadedType.includes('application/gzip') ||
                                            downloadedType.includes('application/x-gzip') ||
                                            downloadedType.includes('application/x-tar');

                                        if (isBlockedType || (!isApkByType && !isApkByDisposition && !isApkByPath)) {
                                            await FileSystem.deleteAsync(downloadResult.uri, { idempotent: true }).catch(() => undefined);
                                            throw new Error(
                                                `업데이트 차단: APK 검증 실패 (content-type=${downloadedType || 'unknown'}, content-disposition=${downloadedDisposition || 'unknown'})`,
                                            );
                                        }

                                        if (!(await Sharing.isAvailableAsync())) {
                                            return {
                                                downloaded: true,
                                                localUri: downloadResult.uri,
                                                contentType: downloadedType || 'application/vnd.android.package-archive',
                                                note: 'Sharing not available on this device',
                                            };
                                        }

                                        await Sharing.shareAsync(downloadResult.uri, {
                                            mimeType: 'application/vnd.android.package-archive',
                                            dialogTitle: 'APK 설치 파일 열기',
                                        });
                                        return {
                                            downloaded: true,
                                            shared: true,
                                            localUri: downloadResult.uri,
                                            contentType: downloadedType || 'application/vnd.android.package-archive',
                                        };
                                    })
                                }
                            >
                                <Text style={styles.buttonText}>APK 다운로드/설치</Text>
                            </Pressable>
                        </View>
                    </View>
                ) : null}

                <View style={styles.outputBox}>
                    <Text style={styles.outputTitle}>Response</Text>
                    <Text style={styles.outputText}>{result}</Text>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safe: {
        flex: 1,
        backgroundColor: '#05070b',
    },
    container: {
        padding: 16,
        gap: 12,
    },
    title: {
        color: '#f8fafc',
        fontSize: 26,
        fontWeight: '700',
    },
    subtitle: {
        color: '#cbd5e1',
        fontSize: 14,
        marginBottom: 4,
    },
    card: {
        backgroundColor: '#0b1220',
        borderColor: '#263044',
        borderWidth: 1,
        borderRadius: 14,
        padding: 12,
        gap: 8,
    },
    label: {
        color: '#e2e8f0',
        fontSize: 13,
        fontWeight: '600',
    },
    input: {
        borderColor: '#334155',
        borderWidth: 1,
        borderRadius: 10,
        color: '#f8fafc',
        backgroundColor: '#111827',
        paddingHorizontal: 12,
        paddingVertical: 10,
        fontSize: 14,
    },
    helper: {
        color: '#93a3b8',
        fontSize: 12,
    },
    row: {
        flexDirection: 'row',
        gap: 8,
    },
    tabRow: {
        flexDirection: 'row',
        gap: 8,
    },
    tabButton: {
        flex: 1,
        borderColor: '#334155',
        borderWidth: 1,
        borderRadius: 999,
        paddingVertical: 9,
        alignItems: 'center',
        backgroundColor: '#0f172a',
    },
    tabButtonActive: {
        borderColor: '#14b8a6',
        backgroundColor: '#102a2a',
    },
    tabText: {
        color: '#dbeafe',
        fontSize: 13,
        fontWeight: '700',
    },
    sectionTitle: {
        color: '#e2e8f0',
        fontSize: 14,
        fontWeight: '700',
    },
    confirmPanel: {
        backgroundColor: '#0f1b2b',
        borderColor: '#1f3b62',
        borderWidth: 1,
        borderRadius: 12,
        padding: 10,
        gap: 8,
    },
    switchRow: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    switchLabel: {
        color: '#dbeafe',
        fontSize: 13,
        fontWeight: '600',
    },
    button: {
        flex: 1,
        backgroundColor: '#1f2937',
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#374151',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 44,
        paddingHorizontal: 12,
    },
    primary: {
        backgroundColor: '#0f766e',
        borderColor: '#115e59',
    },
    buttonText: {
        color: '#f8fafc',
        fontSize: 14,
        fontWeight: '700',
    },
    loader: {
        marginTop: 4,
    },
    errorBox: {
        borderColor: '#7f1d1d',
        borderWidth: 1,
        borderRadius: 12,
        padding: 10,
        backgroundColor: '#1b0909',
        gap: 6,
    },
    errorTitle: {
        color: '#fca5a5',
        fontWeight: '700',
    },
    errorText: {
        color: '#fecaca',
        fontSize: 12,
    },
    outputBox: {
        borderColor: '#1e293b',
        borderWidth: 1,
        borderRadius: 12,
        padding: 12,
        backgroundColor: '#020617',
        minHeight: 240,
    },
    outputTitle: {
        color: '#cbd5e1',
        fontWeight: '700',
        marginBottom: 8,
    },
    outputText: {
        color: '#cbd5e1',
        fontSize: 12,
        lineHeight: 18,
        fontFamily: 'monospace',
    },
});
