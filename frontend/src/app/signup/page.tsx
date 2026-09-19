"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { signupUser } from "@/lib/authApi";

const PASSWORD_PATTERN =
    "(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])(?=.*[^A-Za-z0-9]).{8,}";

export default function SignupPage() {
    const router = useRouter();
    const [name, setName] = useState("");
    const [email, setEmail] = useState("");
    const [confirmEmail, setConfirmEmail] = useState("");
    const [password, setPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [formError, setFormError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const isEmailMatch =
        confirmEmail.length > 0 && email === confirmEmail;
    const isPasswordMatch =
        confirmPassword.length > 0 && password === confirmPassword;

    const handleSignupSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (!isEmailMatch) {
            setFormError("Email addresses do not match.");
            return;
        }

        if (!isPasswordMatch) {
            setFormError("Passwords do not match.");
            return;
        }

        setFormError("");
        setIsSubmitting(true);

        try {
            await signupUser(name, email, password);
            router.push("/login");
        } catch (error) {
            setFormError(
                error instanceof Error
                    ? error.message
                    : "Unable to create your account. Please try again.",
            );
        } finally {
            setIsSubmitting(false);
        }
    };

    const passwordRules = [
        { label: "At least 8 characters", isMet: password.length >= 8 },
        {
            label: "At least 1 uppercase letter",
            isMet: /[A-Z]/.test(password),
        },
        {
            label: "At least 1 lowercase letter",
            isMet: /[a-z]/.test(password),
        },
        { label: "At least 1 number", isMet: /[0-9]/.test(password) },
        {
            label: "At least 1 symbol",
            isMet: /[^A-Za-z0-9]/.test(password),
        },
    ];

    return (
        <main className="signup-page">
            <section className="signup-card" aria-labelledby="signup-title">
                <header className="signup-header">
                    <span className="header-mark" aria-hidden="true">P</span>
                    <h1 id="signup-title">Sign Up</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <div className="signup-content">
                    <div className="welcome-copy">
                        <p className="eyebrow">Start your practice</p>
                        <p className="signup-description">
                            Create an account to build your pronunciation
                            skills.
                        </p>
                    </div>

                    <form
                        className="signup-form"
                        onSubmit={handleSignupSubmit}
                    >
                        <div className="form-field">
                            <label htmlFor="name">Name</label>
                            <input
                                id="name"
                                name="name"
                                type="text"
                                autoComplete="name"
                                placeholder="Enter your name"
                                value={name}
                                onChange={(event) => {
                                    setName(event.target.value);
                                    setFormError("");
                                }}
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
                                value={email}
                                onChange={(event) => {
                                    setEmail(event.target.value);
                                    setFormError("");
                                }}
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
                                value={confirmEmail}
                                onChange={(event) => {
                                    setConfirmEmail(event.target.value);
                                    setFormError("");
                                }}
                                aria-invalid={
                                    confirmEmail.length > 0 && !isEmailMatch
                                }
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
                                    setFormError("");
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
                                value={confirmPassword}
                                onChange={(event) => {
                                    setConfirmPassword(event.target.value);
                                    setFormError("");
                                }}
                                aria-invalid={
                                    confirmPassword.length > 0 &&
                                    !isPasswordMatch
                                }
                                required
                            />
                        </div>

                        <button
                            className="primary-button"
                            type="submit"
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? "Creating account..." : "Sign up"}
                        </button>
                    </form>

                    {formError && (
                        <p className="auth-feedback error" role="alert">
                            {formError}
                        </p>
                    )}

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
