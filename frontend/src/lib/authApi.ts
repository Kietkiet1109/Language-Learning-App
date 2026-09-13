export interface CurrentUser {
    name: string;
}

const API_BASE_URL =
    process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function getApiUrl(path: string) {
    return `${API_BASE_URL}${path}`;
}

export async function getCurrentUser(): Promise<CurrentUser> {
    const response = await fetch(getApiUrl("/auth/me"), {
        credentials: "include",
        cache: "no-store",
    });

    if (!response.ok) {
        throw new Error("Unable to authenticate the current user.");
    }

    const user = (await response.json()) as CurrentUser;

    if (!user.name?.trim()) {
        throw new Error("The authenticated user has no display name.");
    }

    return user;
}

export async function logoutUser() {
    await fetch(getApiUrl("/logout"), {
        method: "POST",
        credentials: "include",
    });
}
