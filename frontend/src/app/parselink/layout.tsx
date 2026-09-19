import type { Metadata } from "next";

export const metadata: Metadata = {
    title: "Learning | Prononcia",
    description: "Begin your pronunciation practice.",
};

export default function RootLayout({children,}: Readonly<{
    children: React.ReactNode;
}>) {
    return children
}
