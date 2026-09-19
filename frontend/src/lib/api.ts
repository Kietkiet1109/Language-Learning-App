const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL;

if (!API_BASE_URL) {
    throw new Error("NEXT_PUBLIC_API_URL is not configured.");
}

export function getApiUrl(path: string): string {
    return `${API_BASE_URL}${path}`;
}
