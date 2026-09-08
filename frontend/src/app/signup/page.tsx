"use client";

import { useState } from "react";
import Link from "next/link";

const PASSWORD_PATTERN =
    "(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,}";

export default function SignupPage() {
    const [password, setPassword] = useState("");

    const passwordRules = [
        {
            label: "At least 8 characters",
            isMet: password.length >= 8,
        },
        {
            label: "At least 1 uppercase letter",
            isMet: /[A-Z]/.test(password),
        },
        {
            label: "At least 1 lowercase letter",
            isMet: /[a-z]/.test(password),
        },
        {
            label: "At least 1 number",
            isMet: /[0-9]/.test(password),
        },
        {
            label: "At least 1 symbol",
            isMet: /[^A-Za-z0-9]/.test(password),
        },
    ];

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
                            <label htmlFor="confirmEmail">Confirm Email</label>
                            <input
                                id="confirmEmail"
                                name="confirmEmail"
                                type="email"
                                autoComplete="email"
                                placeholder="Confirm your email"
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
                                value={password}
                                onChange={(event) => {
                                    setPassword(event.target.value);
                                }}
                                minLength={8}
                                pattern={PASSWORD_PATTERN}
                                required
                            />
                            <ul className="password-rules">
                                {passwordRules.map((rule) => (
                                    <li
                                        className={rule.isMet ? "is-met" : ""}
                                        key={rule.label}
                                    >
                                        {rule.label}
                                    </li>
                                ))}
                            </ul>
                        </div>

                        <div className="form-field">
                            <label htmlFor="confirmPassword">
                                Confirm Password
                            </label>
                            <input
                                id="confirmPassword"
                                name="confirmPassword"
                                type="password"
                                autoComplete="new-password"
                                placeholder="Confirm your password"
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
