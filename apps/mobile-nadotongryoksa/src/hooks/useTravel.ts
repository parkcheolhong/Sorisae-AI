import { useMutation, useQuery } from '@tanstack/react-query';
import {
  callBookingApi,
  callCreatePurchaseApi,
  callInitiatePaymentApi,
  callMyPurchasesApi,
  callNearbyPlacesApi,
} from '../api';
import type { SearchCategory } from '../features/travel-booking/types';

export function useNearbyPlaces(params: {
  lat: string;
  lon: string;
  category: SearchCategory;
  radiusM: number;
  targetLang: string;
  enabled?: boolean;
}) {
  return useQuery({
    queryKey: ['travel', 'nearby', params],
    queryFn: () => callNearbyPlacesApi(params),
    enabled: (params.enabled ?? true) && Boolean(params.lat) && Boolean(params.lon),
    staleTime: 2 * 60 * 1000,
  });
}

export function useTravelActions() {
  const bookingMutation = useMutation({
    mutationFn: (params: {
      token: string;
      placeId: string;
      customerName: string;
      checkinDate: string;
      checkoutDate: string;
      guests: number;
      roomCount: number;
      note: string;
      targetLang: string;
    }) => callBookingApi(params.token, params),
  });

  const createPurchaseMutation = useMutation({
    mutationFn: (params: { token: string; amount: number }) =>
      callCreatePurchaseApi(params.token, params.amount),
  });

  const initiatePaymentMutation = useMutation({
    mutationFn: (params: { token: string; purchaseId: number }) =>
      callInitiatePaymentApi(params.token, params.purchaseId),
  });

  const myPurchasesQuery = (token: string, enabled = true) =>
    useQuery({
      queryKey: ['travel', 'purchases'],
      queryFn: () => callMyPurchasesApi(token),
      enabled: enabled && Boolean(token),
      staleTime: 30 * 1000,
    });

  return {
    bookingMutation,
    createPurchaseMutation,
    initiatePaymentMutation,
    myPurchasesQuery,
  };
}
