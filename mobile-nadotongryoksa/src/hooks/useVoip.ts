import { useMutation, useQuery } from '@tanstack/react-query';
import { fetchVoipCallResumeSnapshot, requestEndVoipCall } from '../api';
import { API_BASE } from '../app/appConstants';

export function useVoip() {
  const resumeCallQuery = (token: string, callId: string, enabled = true) =>
    useQuery({
      queryKey: ['voip', 'resume', callId],
      queryFn: () => fetchVoipCallResumeSnapshot(API_BASE, token, callId),
      enabled: enabled && Boolean(token) && Boolean(callId),
      staleTime: 0,
    });

  const endCallMutation = useMutation({
    mutationFn: (params: { token: string; callId: string; callQuality: string }) =>
      requestEndVoipCall(API_BASE, params.token, params.callId, params.callQuality),
  });

  return {
    resumeCallQuery,
    endCallMutation,
  };
}
