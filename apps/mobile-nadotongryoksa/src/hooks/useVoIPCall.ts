/**
 * VoIP Call Integration Hook
 * Handles VoIP call initialization and state management
 * Can be used in App.tsx or any component that needs to make VoIP calls
 */

import { useState, useCallback, useRef } from 'react';
import { WORLDLINGO_VOIP_CALLER_ID } from '../constants/worldlincoBrand';
import { CallInitResponse } from '../services/voipCallClient';

interface UseVoIPCallOptions {
  apiBaseUrl: string;
  authToken: string;
}

interface VoIPCallState {
  isInitializing: boolean;
  isInCall: boolean;
  callInitResponse: CallInitResponse | null;
  calleePhone: string | null;
  error: string | null;
}

export const useVoIPCall = (options: UseVoIPCallOptions) => {
  const [state, setState] = useState<VoIPCallState>({
    isInitializing: false,
    isInCall: false,
    callInitResponse: null,
    calleePhone: null,
    error: null,
  });

  const callAbortControllerRef = useRef<AbortController | null>(null);

  /**
   * Initiate a VoIP call to a phone number
   * (typically from booking place)
   */
  const startVoIPCall = useCallback(
    async (phoneNumber: string, sessionId?: string) => {
      // Cancel any existing call
      if (callAbortControllerRef.current) {
        callAbortControllerRef.current.abort();
      }

      callAbortControllerRef.current = new AbortController();

      setState((prev) => ({
        ...prev,
        isInitializing: true,
        error: null,
      }));

      try {
        // Call backend to initiate VoIP
        const response = await fetch(`${options.apiBaseUrl}/api/v1/voip/calls/initiate`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${options.authToken}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            callee_phone: phoneNumber,
            caller_id: WORLDLINGO_VOIP_CALLER_ID,
            session_id: sessionId,
          }),
          signal: callAbortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`Failed to initiate call: ${response.statusText}`);
        }

        const callInitResponse: CallInitResponse = await response.json();

        setState((prev) => ({
          ...prev,
          isInitializing: false,
          isInCall: true,
          callInitResponse,
          calleePhone: phoneNumber,
        }));

        return callInitResponse;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : 'Failed to initiate VoIP call';

        setState((prev) => ({
          ...prev,
          isInitializing: false,
          error: errorMessage,
        }));

        throw err;
      }
    },
    [options]
  );

  /**
   * End the current VoIP call
   */
  const endVoIPCall = useCallback(() => {
    if (callAbortControllerRef.current) {
      callAbortControllerRef.current.abort();
    }

    setState((prev) => ({
      ...prev,
      isInCall: false,
      callInitResponse: null,
      calleePhone: null,
    }));
  }, []);

  return {
    ...state,
    startVoIPCall,
    endVoIPCall,
  };
};
