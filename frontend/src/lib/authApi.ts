import { getApiUrl } from "./api";

export interface CurrentUser {
    id: string;
    name: string;
    email: string;
}

export function getFacebookLoginUrl(): string {
    return getApiUrl("/auth/facebook/login");
}

export function getGoogleLoginUrl(): string {
    return getApiUrl("/auth/google/login");
}

interface AuthUser {
    id: string;
    name: string;
    email: string;
}

export interface AuthResponse {
    user: AuthUser;
}

interface ApiError {
    detail?: string;
}

export interface PasswordResetVerification {
    reset_token: string;
}

interface PasswordResetMessage {
    message: string;
}

async function requestApi<T>(
    endpoint: string,
    payload: Record<string, string>,
): Promise<T> {
    const response = await fetch(getApiUrl(endpoint), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(payload),
    });

    if (!response.ok) {
        const errorBody = (await response.json()) as ApiError;
        throw new Error(errorBody.detail ?? "Authentication failed.");
    }

    return (await response.json()) as T;
}

export function signupUser(
    name: string,
    email: string,
    password: string,
): Promise<AuthResponse> {
    return requestApi<AuthResponse>("/auth/signup", {
        name,
        email,
        password,
    });
}

export function loginUser(
    email: string,
    password: string,
): Promise<AuthResponse> {
    return requestApi<AuthResponse>("/auth/login", { email, password });
}

export function requestPasswordReset(
    email: string,
): Promise<PasswordResetMessage> {
    return requestApi<PasswordResetMessage>("/auth/password-reset/request", {
        email,
    });
}

export function verifyPasswordReset(
    email: string,
    code: string,
): Promise<PasswordResetVerification> {
    return requestApi<PasswordResetVerification>(
        "/auth/password-reset/verify",
        { email, code },
    );
}

export function confirmPasswordReset(
    resetToken: string,
    newPassword: string,
): Promise<PasswordResetMessage> {
    return requestApi<PasswordResetMessage>(
        "/auth/password-reset/confirm",
        { reset_token: resetToken, new_password: newPassword },
    );
}

export async function getCurrentUser(): Promise<CurrentUser> {
    const response = await fetch(getApiUrl("/auth/me"), {
        credentials: "include",
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error("Unable to authenticate the current user.");
    }

    const body = (await response.json()) as AuthResponse;
    const user = body.user;

    if (!user.name?.trim()) {
        throw new Error("The authenticated user has no display name.");
    }

    return user;
}

export async function logoutUser() {
    await fetch(getApiUrl("/auth/logout"), {
        method: "POST",
        credentials: "include",
    });
}
