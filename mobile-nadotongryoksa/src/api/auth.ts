import { AUTH_API_ERROR_TEXT } from '../app/appConstants';
import {
  callLoginApi as callLoginApiBase,
  callMeApi,
  callLogoutApi as callLogoutApiBase,
  callSignupApi as callSignupApiBase,
  callSignupConfirmApi as callSignupConfirmApiBase,
  callSignupRequestCodeApi as callSignupRequestCodeApiBase,
  callUpdateMeApi as callUpdateMeApiBase,
} from '../app/appApiClient';
import type {
  SignupPayload,
  SignupRequestCodeResponse,
  UserInfo,
  UserProfileUpdatePayload,
} from '../app/appTypes';

const currentUserRequestCache = new Map<string, Promise<UserInfo>>();
const currentUserResponseCache = new Map<string, UserInfo>();

export function clearCurrentUserCache(token?: string): void {
  if (token) {
    const normalizedToken = token.trim();
    if (normalizedToken) {
      currentUserRequestCache.delete(normalizedToken);
      currentUserResponseCache.delete(normalizedToken);
    }
    return;
  }

  currentUserRequestCache.clear();
  currentUserResponseCache.clear();
}

export async function callLoginApi(email: string, password: string): Promise<string> {
  return callLoginApiBase(email, password);
}

export async function callSignupApi(payload: SignupPayload): Promise<UserInfo> {
  return callSignupApiBase(payload);
}

export async function callSignupRequestCodeApi(payload: SignupPayload): Promise<SignupRequestCodeResponse> {
  return callSignupRequestCodeApiBase(payload);
}

export async function callSignupConfirmApi(
  signupSessionToken: string,
  verificationCode: string,
  profile: Pick<SignupPayload, 'preferred_language' | 'country_code' | 'full_name'>,
): Promise<UserInfo> {
  return callSignupConfirmApiBase(signupSessionToken, verificationCode, profile);
}

export async function getCurrentUserApi(token: string, forceRefresh = false): Promise<UserInfo> {
  const normalizedToken = token.trim();
  if (!normalizedToken) {
    throw new Error(AUTH_API_ERROR_TEXT.meFetchFailed);
  }

  if (!forceRefresh) {
    const cachedUser = currentUserResponseCache.get(normalizedToken);
    if (cachedUser) {
      return cachedUser;
    }
  }

  const cachedRequest = currentUserRequestCache.get(normalizedToken);
  if (cachedRequest) {
    return cachedRequest;
  }

  const request = (async () => {
    const userInfo = await callMeApi(normalizedToken);
    currentUserResponseCache.set(normalizedToken, userInfo);
    return userInfo;
  })();

  currentUserRequestCache.set(normalizedToken, request);
  try {
    return await request;
  } finally {
    if (currentUserRequestCache.get(normalizedToken) === request) {
      currentUserRequestCache.delete(normalizedToken);
    }
  }
}

export async function callLogoutApi(token: string): Promise<void> {
  await callLogoutApiBase(token);
}

export async function callUpdateMeApi(token: string, payload: UserProfileUpdatePayload): Promise<UserInfo> {
  const userInfo = await callUpdateMeApiBase(token, payload);
  const normalizedToken = token.trim();
  if (normalizedToken) {
    currentUserResponseCache.set(normalizedToken, userInfo);
  }
  return userInfo;
}
