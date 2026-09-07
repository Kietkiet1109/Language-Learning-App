import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
    title: "Signup | Prononcia",
    description: "Create your Prononcia account and begin practicing.",
};

export default function SignupPage() {
    return (
        <main className="signup-page">
            <section className="signup-card" aria-labelledby="signup-title">
                <header className="signup-header">
                    <span className="header-mark" aria-hidden="true">
                        P
                    </span>
                    <h1 id="signup-title">Sign Up</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <div className="signup-content">
                    <div className="welcome-copy">
                        <p className="eyebrow">Start your practice</p>
                        <p className="signup-description">
                            Create an account to build your
                            pronunciation skills with Prononcia.
                        </p>
                    </div>

                    <form className="signup-form">
                        <div className="form-field">
                            <label htmlFor="name">Name</label>
                            <input
                                id="name"
                                name="name"
                                type="text"
                                autoComplete="name"
                                placeholder="Enter your name"
                                required
                            />
                        </div>

                        <div className="form-field">
                            <label htmlFor="email">Email</label>
                            <input
                                id="email"
                                name="email"
                                type="email"
                                autoComplete="email"
                                placeholder="you@example.com"
                                required
                            />
                        </div>

                        <div className="form-field">
                            <label htmlFor="password">Password</label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="new-password"
                                placeholder="Create a password"
                                required
                            />
                        </div>

                        <button className="primary-button" type="submit">
                            Sign up
                        </button>
                    </form>

                    <p className="signup-prompt">
                        Already have an account?{" "}
                        <Link className="text-link" href="/login">
                            Log in
                        </Link>
                    </p>
                </div>
            </section>
        </main>
    );
}
