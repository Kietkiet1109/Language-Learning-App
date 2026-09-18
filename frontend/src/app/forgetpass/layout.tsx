import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Forgot Password | Prononcia",
    description: "Request a verification code to reset your password.",
};

export default function ForgotPasswordLayout({children,}: Readonly<{
    children: React.ReactNode;
}>) {
    return children;
}
