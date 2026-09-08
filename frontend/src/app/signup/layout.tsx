import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Signup | Prononcia",
    description: "Create your Prononcia account and begin practicing.",
};

export default function SignupLayout({children,}: Readonly<{
    children: React.ReactNode;
}>) {
    return children;
}
