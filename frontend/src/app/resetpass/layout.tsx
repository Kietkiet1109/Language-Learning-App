import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Reset Password | Prononcia",
    description: "Create a new password for your Prononcia account.",
};

export default function ResetPasswordLayout({children,}: Readonly<{
    children: React.ReactNode;
}>) {
    return children;
}
