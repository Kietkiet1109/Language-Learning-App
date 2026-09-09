const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface AuthUser {
    id: string;
    name: string;
    email: string;
}

interface AuthResponse {
    user: AuthUser;
}

interface ApiError {
    detail?: string;
}

async function requestAuth(
    endpoint: string,
    payload: Record<string, string>,
): Promise<AuthResponse> {
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

    return (await response.json()) as AuthResponse;
}

export function signupUser(
    name: string,
    email: string,
    password: string,
): Promise<AuthResponse> {
    return requestAuth("/auth/signup", { name, email, password });
}

export function loginUser(
    email: string,
    password: string,
): Promise<AuthResponse> {
    return requestAuth("/auth/login", { email, password });
}
