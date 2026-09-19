import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Login | Prononcia",
    description: "Continue your pronunciation journey with Prononcia.",
};

export default function LoginLayout({children,}: Readonly<{
    children: React.ReactNode;
}>) {
    return children;
}
