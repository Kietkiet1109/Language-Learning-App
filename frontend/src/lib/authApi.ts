const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
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
