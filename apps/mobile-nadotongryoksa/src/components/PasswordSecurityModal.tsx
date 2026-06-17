import React, { useCallback, useEffect, useState } from 'react';
import {
    ActivityIndicator,
    Modal,
    Pressable,
    StyleSheet,
    Text,
    TextInput,
    View,
} from 'react-native';
import {
    authenticateWithBiometric,
    isBiometricAvailable,
    isBiometricLoginEnabled,
    saveBiometricCredentials,
    updateBiometricStoredPassword,
} from '../auth/biometricGate';
import {
    changeUserPassword,
    resetUserPasswordViaRecovery,
    startUserPasswordRecovery,
    verifyUserPasswordRecovery,
} from '../auth/passwordSecurityApi';

type PasswordSecurityMode = 'recover' | 'change';

type PasswordSecurityModalProps = {
    visible: boolean;
    mode: PasswordSecurityMode;
    apiBase: string;
    authToken?: string;
    defaultEmail?: string;
    onClose: () => void;
    onCompleted?: (payload: { email: string; newPassword?: string; mustRelogin?: boolean }) => void;
};

const C = {
    bg: '#0b0f16',
    panel: '#151b23',
    border: '#21262d',
    text: '#e6edf3',
    sub: '#8b949e',
    accent: '#2a7cff',
    danger: '#ffb4b4',
    ok: '#7ee787',
};

type Step = 'form' | 'verify' | 'reset' | 'change';

export function PasswordSecurityModal({
    visible,
    mode,
    apiBase,
    authToken,
    defaultEmail = '',
    onClose,
    onCompleted,
}: PasswordSecurityModalProps) {
    const [step, setStep] = useState<Step>(mode === 'change' ? 'change' : 'form');
    const [email, setEmail] = useState(defaultEmail);
    const [verificationCode, setVerificationCode] = useState('');
    const [recoverySessionToken, setRecoverySessionToken] = useState('');
    const [resetToken, setResetToken] = useState('');
    const [maskedTarget, setMaskedTarget] = useState('');
    const [devOtpHint, setDevOtpHint] = useState('');
    const [currentPassword, setCurrentPassword] = useState('');
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [message, setMessage] = useState('');
    const [biometricReady, setBiometricReady] = useState(false);
    const [biometricLoginEnabled, setBiometricLoginEnabledState] = useState(false);
    const [enableBiometricAfterChange, setEnableBiometricAfterChange] = useState(false);

    const resetState = useCallback(() => {
        setStep(mode === 'change' ? 'change' : 'form');
        setEmail(defaultEmail);
        setVerificationCode('');
        setRecoverySessionToken('');
        setResetToken('');
        setMaskedTarget('');
        setDevOtpHint('');
        setCurrentPassword('');
        setNewPassword('');
        setConfirmPassword('');
        setLoading(false);
        setError('');
        setMessage('');
        setEnableBiometricAfterChange(false);
    }, [defaultEmail, mode]);

    useEffect(() => {
        if (!visible) {
            return;
        }
        resetState();
        void (async () => {
            setBiometricReady(await isBiometricAvailable());
            setBiometricLoginEnabledState(await isBiometricLoginEnabled());
        })();
    }, [visible, resetState]);

    const requireBiometric = async (reason: string): Promise<boolean> => {
        if (!biometricReady) {
            return true;
        }
        const ok = await authenticateWithBiometric(reason);
        if (!ok) {
            setError('생체 인증에 실패했습니다. 다시 시도해 주세요.');
        }
        return ok;
    };

    const handleStartRecovery = async () => {
        if (!email.trim()) {
            setError('이메일을 입력해 주세요.');
            return;
        }
        setLoading(true);
        setError('');
        setMessage('');
        try {
            const payload = await startUserPasswordRecovery(apiBase, email.trim(), 'email');
            setRecoverySessionToken(payload.recovery_session_token);
            setMaskedTarget(payload.masked_target);
            setDevOtpHint(String(payload.dev_otp_hint || ''));
            setStep('verify');
            setMessage(`${payload.masked_target}(으)로 인증 코드를 보냈습니다.`);
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : '인증 코드 발송에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleVerifyRecovery = async () => {
        if (!verificationCode.trim()) {
            setError('6자리 인증 코드를 입력해 주세요.');
            return;
        }
        setLoading(true);
        setError('');
        try {
            const payload = await verifyUserPasswordRecovery(apiBase, recoverySessionToken, verificationCode);
            setResetToken(payload.reset_token);
            setStep('reset');
            setMessage('본인 확인이 완료되었습니다. 새 비밀번호를 설정해 주세요.');
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : '인증 코드 확인에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleResetPassword = async () => {
        if (newPassword.length < 8) {
            setError('비밀번호는 8자 이상이어야 합니다.');
            return;
        }
        if (newPassword !== confirmPassword) {
            setError('새 비밀번호 확인이 일치하지 않습니다.');
            return;
        }
        if (!(await requireBiometric('비밀번호 재설정을 위해 본인 확인'))) {
            return;
        }
        setLoading(true);
        setError('');
        try {
            await resetUserPasswordViaRecovery(apiBase, resetToken, newPassword);
            if (enableBiometricAfterChange && biometricReady) {
                await saveBiometricCredentials({ email: email.trim(), password: newPassword });
            }
            onCompleted?.({ email: email.trim(), newPassword, mustRelogin: true });
            onClose();
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : '비밀번호 재설정에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const handleChangePassword = async () => {
        if (!authToken) {
            setError('로그인 상태가 아닙니다.');
            return;
        }
        if (!currentPassword.trim() || !newPassword.trim()) {
            setError('현재 비밀번호와 새 비밀번호를 입력해 주세요.');
            return;
        }
        if (newPassword.length < 8) {
            setError('비밀번호는 8자 이상이어야 합니다.');
            return;
        }
        if (newPassword !== confirmPassword) {
            setError('새 비밀번호 확인이 일치하지 않습니다.');
            return;
        }
        if (!(await requireBiometric('비밀번호 변경을 위해 본인 확인'))) {
            return;
        }
        setLoading(true);
        setError('');
        try {
            await changeUserPassword(apiBase, authToken, currentPassword, newPassword);
            if (biometricLoginEnabled) {
                await updateBiometricStoredPassword(newPassword);
            } else if (enableBiometricAfterChange && biometricReady) {
                await saveBiometricCredentials({
                    email: defaultEmail.trim(),
                    password: newPassword,
                });
            }
            onCompleted?.({ email: defaultEmail.trim(), newPassword, mustRelogin: true });
            onClose();
        } catch (e: unknown) {
            setError(e instanceof Error ? e.message : '비밀번호 변경에 실패했습니다.');
        } finally {
            setLoading(false);
        }
    };

    const title = mode === 'change' ? '🔒 비밀번호 변경' : '🔑 비밀번호 찾기';

    return (
        <Modal visible={visible} transparent animationType="fade" onRequestClose={onClose}>
            <View style={styles.overlay}>
                <View style={styles.panel} accessibilityLabel="worldlinco-password-security-modal" testID="worldlinco-password-security-modal">
                    <Text style={styles.title}>{title}</Text>
                    {biometricReady ? (
                        <Text style={styles.hint}>지문/얼굴 인식으로 본인 확인 후 비밀번호를 변경합니다.</Text>
                    ) : (
                        <Text style={styles.hint}>이 기기는 생체 인증을 지원하지 않아 비밀번호 입력으로 진행합니다.</Text>
                    )}

                    {mode === 'recover' && step === 'form' ? (
                        <>
                            <TextInput
                                style={styles.input}
                                placeholder="가입 이메일"
                                placeholderTextColor={C.sub}
                                autoCapitalize="none"
                                keyboardType="email-address"
                                value={email}
                                onChangeText={setEmail}
                                testID="worldlinco-password-recover-email"
                            />
                            <Pressable style={styles.primaryBtn} onPress={() => { void handleStartRecovery(); }} disabled={loading}>
                                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryBtnText}>인증 코드 받기</Text>}
                            </Pressable>
                        </>
                    ) : null}

                    {mode === 'recover' && step === 'verify' ? (
                        <>
                            <Text style={styles.message}>{message}</Text>
                            {devOtpHint ? <Text style={styles.devHint}>개발 OTP: {devOtpHint}</Text> : null}
                            <TextInput
                                style={styles.input}
                                placeholder="6자리 인증 코드"
                                placeholderTextColor={C.sub}
                                keyboardType="number-pad"
                                value={verificationCode}
                                onChangeText={setVerificationCode}
                                testID="worldlinco-password-recover-otp"
                            />
                            <Pressable style={styles.primaryBtn} onPress={() => { void handleVerifyRecovery(); }} disabled={loading}>
                                {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.primaryBtnText}>본인 확인</Text>}
                            </Pressable>
                        </>
                    ) : null}

                    {(mode === 'recover' && step === 'reset') || (mode === 'change' && step === 'change') ? (
                        <>
                            {mode === 'change' ? (
                                <TextInput
                                    style={styles.input}
                                    placeholder="현재 비밀번호"
                                    placeholderTextColor={C.sub}
                                    secureTextEntry
                                    value={currentPassword}
                                    onChangeText={setCurrentPassword}
                                    testID="worldlinco-password-change-current"
                                />
                            ) : (
                                <Text style={styles.message}>{maskedTarget ? `${maskedTarget} 인증 완료` : message}</Text>
                            )}
                            <TextInput
                                style={styles.input}
                                placeholder="새 비밀번호 (8자 이상)"
                                placeholderTextColor={C.sub}
                                secureTextEntry
                                value={newPassword}
                                onChangeText={setNewPassword}
                                testID="worldlinco-password-new"
                            />
                            <TextInput
                                style={styles.input}
                                placeholder="새 비밀번호 확인"
                                placeholderTextColor={C.sub}
                                secureTextEntry
                                value={confirmPassword}
                                onChangeText={setConfirmPassword}
                                testID="worldlinco-password-new-confirm"
                            />
                            {biometricReady && !biometricLoginEnabled ? (
                                <Pressable
                                    style={styles.toggleRow}
                                    onPress={() => setEnableBiometricAfterChange((prev) => !prev)}
                                    testID="worldlinco-password-enable-biometric"
                                >
                                    <Text style={styles.toggleText}>
                                        {enableBiometricAfterChange ? '☑' : '☐'} 변경 후 지문으로 빠른 로그인 사용
                                    </Text>
                                </Pressable>
                            ) : null}
                            <Pressable
                                style={styles.primaryBtn}
                                onPress={() => { void (mode === 'change' ? handleChangePassword() : handleResetPassword()); }}
                                disabled={loading}
                                testID="worldlinco-password-submit"
                            >
                                {loading ? (
                                    <ActivityIndicator color="#fff" />
                                ) : (
                                    <Text style={styles.primaryBtnText}>{mode === 'change' ? '비밀번호 변경' : '새 비밀번호 저장'}</Text>
                                )}
                            </Pressable>
                        </>
                    ) : null}

                    {error ? <Text style={styles.error}>{error}</Text> : null}
                    {message && step !== 'verify' && step !== 'reset' ? <Text style={styles.message}>{message}</Text> : null}

                    <Pressable style={styles.closeBtn} onPress={onClose}>
                        <Text style={styles.closeBtnText}>닫기</Text>
                    </Pressable>
                </View>
            </View>
        </Modal>
    );
}

const styles = StyleSheet.create({
    overlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.72)',
        justifyContent: 'center',
        padding: 20,
    },
    panel: {
        backgroundColor: C.panel,
        borderRadius: 16,
        borderWidth: 1,
        borderColor: C.border,
        padding: 20,
        gap: 10,
    },
    title: {
        color: C.text,
        fontSize: 18,
        fontWeight: '800',
    },
    hint: {
        color: C.sub,
        fontSize: 13,
        lineHeight: 18,
    },
    input: {
        borderRadius: 10,
        borderWidth: 1,
        borderColor: C.border,
        backgroundColor: C.bg,
        color: C.text,
        paddingHorizontal: 12,
        paddingVertical: 11,
    },
    primaryBtn: {
        backgroundColor: C.accent,
        borderRadius: 10,
        paddingVertical: 12,
        alignItems: 'center',
    },
    primaryBtnText: {
        color: '#fff',
        fontWeight: '800',
    },
    closeBtn: {
        alignSelf: 'flex-end',
        paddingVertical: 6,
    },
    closeBtnText: {
        color: C.sub,
        fontWeight: '700',
    },
    error: {
        color: C.danger,
        fontSize: 13,
    },
    message: {
        color: C.ok,
        fontSize: 13,
    },
    devHint: {
        color: '#f0c674',
        fontSize: 12,
    },
    toggleRow: {
        paddingVertical: 4,
    },
    toggleText: {
        color: C.text,
        fontSize: 13,
    },
});
