'use client';

import { useCallback, useRef, useState } from 'react';

type BrowserSpeechRecognition = {
    lang: string;
    interimResults: boolean;
    maxAlternatives: number;
    onresult: ((event: { results?: Array<Array<{ transcript?: string }>> }) => void) | null;
    onerror: ((event: { error?: string }) => void) | null;
    onend: (() => void) | null;
    start: () => void;
    stop: () => void;
};

type SpeechRecognitionWindow = Window & {
    SpeechRecognition?: new () => BrowserSpeechRecognition;
    webkitSpeechRecognition?: new () => BrowserSpeechRecognition;
};

export type UseOrchestratorVoiceSttOptions = {
    onTranscript: (transcript: string) => void | Promise<void>;
    onUnsupported?: () => void;
    onError?: (detail: string) => void;
    lang?: string;
};

export function useOrchestratorVoiceStt(options: UseOrchestratorVoiceSttOptions) {
    const [listening, setListening] = useState(false);
    const recognitionRef = useRef<BrowserSpeechRecognition | null>(null);

    const stopListening = useCallback(() => {
        recognitionRef.current?.stop();
    }, []);

    const startListening = useCallback(() => {
        if (typeof window === 'undefined') {
            return;
        }
        if (listening) {
            stopListening();
            return;
        }

        const speechWindow = window as SpeechRecognitionWindow;
        const SpeechRecognitionCtor = speechWindow.SpeechRecognition || speechWindow.webkitSpeechRecognition;
        if (!SpeechRecognitionCtor) {
            options.onUnsupported?.();
            return;
        }

        const recognition = new SpeechRecognitionCtor();
        recognition.lang = options.lang || 'ko-KR';
        recognition.interimResults = false;
        recognition.maxAlternatives = 1;
        recognition.onresult = async (event) => {
            const transcript = String(event?.results?.[0]?.[0]?.transcript || '').trim();
            if (transcript) {
                await options.onTranscript(transcript);
            }
        };
        recognition.onerror = (event) => {
            options.onError?.(String(event?.error || 'unknown'));
        };
        recognition.onend = () => {
            setListening(false);
            recognitionRef.current = null;
        };
        recognitionRef.current = recognition;
        setListening(true);
        recognition.start();
    }, [listening, options, stopListening]);

    return {
        listening,
        startListening,
        stopListening,
    };
}
