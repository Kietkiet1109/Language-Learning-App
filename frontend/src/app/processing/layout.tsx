import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Processing | Prononcia",
    description: "Preparing your pronunciation lesson.",
};

export default function ProcessingLayout({
    children,
}: Readonly<{
    children: React.ReactNode;
}>) {
    return children;
}
