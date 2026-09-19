import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Learning | Prononcia",
    description: "Practice your pronunciation sentence by sentence.",
};

export default function RecordLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return children;
}
