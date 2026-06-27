import React from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

type VoipCallErrorBoundaryProps = {
    children: React.ReactNode;
    onRecover: () => void;
};

type VoipCallErrorBoundaryState = {
    hasError: boolean;
    message: string;
};

export class VoipCallErrorBoundary extends React.Component<
    VoipCallErrorBoundaryProps,
    VoipCallErrorBoundaryState
> {
    constructor(props: VoipCallErrorBoundaryProps) {
        super(props);
        this.state = { hasError: false, message: '' };
    }

    static getDerivedStateFromError(error: unknown): VoipCallErrorBoundaryState {
        const message = error instanceof Error ? error.message : '통화 화면에서 오류가 발생했습니다.';
        return { hasError: true, message };
    }

    componentDidCatch(error: unknown) {
        console.error('[VoipCallErrorBoundary] render failure', error);
    }

    private handleRecover = () => {
        this.setState({ hasError: false, message: '' });
        this.props.onRecover();
    };

    render() {
        if (this.state.hasError) {
            return (
                <View style={styles.container}>
                    <Text style={styles.title}>통화 화면 오류</Text>
                    <Text style={styles.message}>{this.state.message}</Text>
                    <Pressable style={styles.button} onPress={this.handleRecover}>
                        <Text style={styles.buttonText}>다시 시도</Text>
                    </Pressable>
                </View>
            );
        }

        return this.props.children;
    }
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        padding: 24,
        backgroundColor: '#0b0f16',
    },
    title: {
        color: '#f5f7fb',
        fontSize: 18,
        fontWeight: '700',
        marginBottom: 12,
    },
    message: {
        color: '#b8c0cc',
        fontSize: 14,
        textAlign: 'center',
        marginBottom: 20,
    },
    button: {
        backgroundColor: '#2f6fed',
        borderRadius: 10,
        paddingHorizontal: 18,
        paddingVertical: 12,
    },
    buttonText: {
        color: '#ffffff',
        fontSize: 14,
        fontWeight: '600',
    },
});
