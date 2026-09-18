import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Feedback | Prononcia",
    description: "Review your pronunciation practice result.",
};

export default function ResultLayout({children,}: Readonly<{
    children: React.ReactNode;
}>) {
    return children;
}
