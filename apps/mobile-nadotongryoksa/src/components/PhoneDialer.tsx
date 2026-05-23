/**
 * Phone Dialer Component
 * Provides UI for phone number input and call initiation
 */

import React, { useState, useCallback, useEffect } from 'react';
import {
    View,
    Text,
    TextInput,
    TouchableOpacity,
    StyleSheet,
    SafeAreaView,
    ScrollView,
    ActivityIndicator,
} from 'react-native';

interface PhoneDialerProps {
    onCallInitiated: (phoneNumber: string) => void;
    onCancel?: () => void;
    isLoading?: boolean;
    defaultPhone?: string;
}

export const PhoneDialer: React.FC<PhoneDialerProps> = ({
    onCallInitiated,
    onCancel,
    isLoading = false,
    defaultPhone = '+82-',
}) => {
    const [phoneNumber, setPhoneNumber] = useState(defaultPhone);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        setPhoneNumber(defaultPhone || '+82-');
        setError(null);
    }, [defaultPhone]);

    // Validate phone number format
    const validatePhoneNumber = useCallback((phone: string): boolean => {
        const trimmed = phone.trim();
        
        if (!trimmed.startsWith('+')) {
            setError('전화번호는 +국가번호로 시작해야 합니다');
            return false;
        }

        const digitOnly = trimmed.replace(/[^\d+]/g, '');
        if (digitOnly.length < 10 || digitOnly.length > 15) {
            setError('전화번호는 10-15자리 숫자여야 합니다');
            return false;
        }

        setError(null);
        return true;
    }, []);

    const handleCallPress = useCallback(() => {
        if (!validatePhoneNumber(phoneNumber)) {
            return;
        }
        onCallInitiated(phoneNumber.trim());
    }, [phoneNumber, validatePhoneNumber, onCallInitiated]);

    const handlePhoneChange = (text: string) => {
        setPhoneNumber(text);
        setError(null);
    };

    return (
        <SafeAreaView style={styles.container}>
            <ScrollView contentContainerStyle={styles.content}>
                {/* Header */}
                <View style={styles.header}>
                    <Text style={styles.title}>다이얼패드</Text>
                    <Text style={styles.subtitle}>전화번호를 입력하여 통화를 시작하세요</Text>
                </View>

                {/* Phone Input Card */}
                <View style={styles.card}>
                    <Text style={styles.label}>전화번호</Text>
                    <TextInput
                        style={[
                            styles.phoneInput,
                            error ? styles.phoneInputError : null,
                        ]}
                        placeholder="+82-1234-5678"
                        placeholderTextColor="#999"
                        value={phoneNumber}
                        onChangeText={handlePhoneChange}
                        editable={!isLoading}
                        keyboardType="phone-pad"
                    />
                    {error && <Text style={styles.errorText}>{error}</Text>}
                    <Text style={styles.hint}>예: +82-10-1234-5678 (국가번호 필수)</Text>
                </View>

                {/* Format Guide */}
                <View style={styles.guideCard}>
                    <Text style={styles.guideTitle}>📋 형식 안내</Text>
                    <Text style={styles.guideItem}>• +로 시작</Text>
                    <Text style={styles.guideItem}>• 국가번호 포함 (예: 82)</Text>
                    <Text style={styles.guideItem}>• 총 10-15자리 숫자</Text>
                    <Text style={styles.guideItem}>• 하이픈(-) 입력 가능</Text>
                </View>

                {/* Call Button */}
                <TouchableOpacity
                    style={[
                        styles.callButton,
                        isLoading ? styles.callButtonDisabled : null,
                    ]}
                    onPress={handleCallPress}
                    disabled={isLoading}
                >
                    {isLoading ? (
                        <ActivityIndicator color="#fff" />
                    ) : (
                        <Text style={styles.callButtonText}>📞 통화 시작</Text>
                    )}
                </TouchableOpacity>

                {/* Close Button */}
                {onCancel && (
                    <TouchableOpacity
                        style={styles.closeButton}
                        onPress={onCancel}
                        disabled={isLoading}
                    >
                        <Text style={styles.closeButtonText}>닫기</Text>
                    </TouchableOpacity>
                )}

                {/* Recent Numbers (Optional Enhancement) */}
                <View style={styles.recentCard}>
                    <Text style={styles.recentTitle}>빠른 입력</Text>
                    <TouchableOpacity
                        style={styles.recentButton}
                        onPress={() => handlePhoneChange('+82-')}
                    >
                        <Text style={styles.recentButtonText}>+82-</Text>
                    </TouchableOpacity>
                </View>
            </ScrollView>
        </SafeAreaView>
    );
};

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#f5f5f5',
    },
    content: {
        padding: 16,
    },
    header: {
        marginBottom: 24,
        alignItems: 'center',
    },
    title: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#222',
        marginBottom: 8,
    },
    subtitle: {
        fontSize: 14,
        color: '#666',
        textAlign: 'center',
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    label: {
        fontSize: 16,
        fontWeight: '600',
        color: '#222',
        marginBottom: 8,
    },
    phoneInput: {
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 8,
        paddingHorizontal: 12,
        paddingVertical: 12,
        fontSize: 16,
        marginBottom: 8,
        color: '#222',
    },
    phoneInputError: {
        borderColor: '#ff6b6b',
    },
    errorText: {
        color: '#ff6b6b',
        fontSize: 12,
        marginBottom: 8,
    },
    hint: {
        fontSize: 12,
        color: '#999',
    },
    guideCard: {
        backgroundColor: '#e7f5ff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 16,
        borderLeftWidth: 4,
        borderLeftColor: '#1971c2',
    },
    guideTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#1971c2',
        marginBottom: 8,
    },
    guideItem: {
        fontSize: 13,
        color: '#1971c2',
        marginBottom: 4,
    },
    callButton: {
        backgroundColor: '#4CAF50',
        borderRadius: 12,
        paddingVertical: 16,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.3,
        shadowRadius: 8,
        elevation: 5,
    },
    callButtonDisabled: {
        backgroundColor: '#ccc',
    },
    callButtonText: {
        fontSize: 18,
        fontWeight: '600',
        color: '#fff',
    },
    closeButton: {
        borderWidth: 1,
        borderColor: '#ddd',
        borderRadius: 12,
        paddingVertical: 12,
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 16,
    },
    closeButtonText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#666',
    },
    recentCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 3,
    },
    recentTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#222',
        marginBottom: 12,
    },
    recentButton: {
        paddingVertical: 10,
        paddingHorizontal: 12,
        borderRadius: 8,
        backgroundColor: '#f0f0f0',
    },
    recentButtonText: {
        fontSize: 14,
        color: '#1971c2',
        fontWeight: '500',
    },
});
