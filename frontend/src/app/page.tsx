import Link from "next/link";

export default function Home() {
    return (
        <main className="home-page">
            <p>Welcome to Prononcia</p>
            <Link className="home-link" href="/login">Go to login</Link>
        </main>
    );
}
