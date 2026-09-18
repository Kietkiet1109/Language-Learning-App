"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    getFacebookLoginUrl,
    getGoogleLoginUrl,
    loginUser,
} from "@/lib/authApi";

export default function LoginPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [formError, setFormError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [isFacebookSubmitting, setIsFacebookSubmitting] = useState(false);
    const [isGoogleSubmitting, setIsGoogleSubmitting] = useState(false);

    useEffect(() => {
        const query = new URLSearchParams(window.location.search);
        const facebookErrorCode = query.get("facebook_error");
        const googleErrorCode = query.get("google_error");
        const messages: Record<string, string> = {
            facebook_not_configured:
                "Facebook Login is not configured on the server.",
            facebook_state_invalid:
                "Facebook Login expired. Please try again.",
            facebook_cancelled:
                "Facebook Login was cancelled.",
            facebook_login_failed:
                "Facebook Login could not be completed.",
            facebook_account_link_failed:
                "Your Facebook account could not be linked.",
            google_not_configured:
                "Google Login is not configured on the server.",
            google_state_invalid:
                "Google Login expired. Please try again.",
            google_cancelled: "Google Login was cancelled.",
            google_login_failed: "Google Login could not be completed.",
            google_account_link_failed:
                "Your Google account could not be linked.",
        };
        const errorCode = facebookErrorCode ?? googleErrorCode;
        if (errorCode && messages[errorCode]) {
            setFormError(messages[errorCode]);
            window.history.replaceState({}, "", "/login");
        }
    }, []);

    const handleLoginSubmit = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setFormError("");
        setIsSubmitting(true);

        try {
            await loginUser(email, password);
            router.push("/");
        } catch (error) {
            setFormError(
                error instanceof Error
                    ? error.message
                    : "Unable to log in. Please try again.",
            );
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleFacebookLogin = () => {
        setFormError("");
        setIsFacebookSubmitting(true);
        window.location.assign(getFacebookLoginUrl());
    };

    const handleGoogleLogin = () => {
        setFormError("");
        setIsGoogleSubmitting(true);
        window.location.assign(getGoogleLoginUrl());
    };

    return (
        <main className="login-page">
            <section className="login-card" aria-labelledby="login-title">
                <header className="login-header">
                    <span className="header-mark" aria-hidden="true">P</span>
                    <h1 id="login-title">Login</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <div className="login-content">
                    <div className="welcome-copy">
                        <p className="eyebrow">Welcome to Prononcia</p>
                        <p className="login-description">
                            Continue your journey to clearer pronunciation.
                        </p>
                    </div>

                    <form
                        className="login-form"
                        onSubmit={handleLoginSubmit}
                    >
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
                            <label htmlFor="password">Password</label>
                            <input
                                id="password"
                                name="password"
                                type="password"
                                autoComplete="current-password"
                                placeholder="Enter your password"
                                value={password}
                                onChange={(event) => {
                                    setPassword(event.target.value);
                                    setFormError("");
                                }}
                                required
                            />
                        </div>

                        <div className="form-options">
                            <label className="remember-option">
                                <input type="checkbox" name="rememberMe" />
                                <span>Remember me</span>
                            </label>
                            <Link className="text-link" href="/forgetpass">
                                Forget your Password?
                            </Link>
                        </div>

                        <button
                            className="primary-button"
                            type="submit"
                            disabled={isSubmitting}
                        >
                            {isSubmitting ? "Logging in..." : "Log In"}
                        </button>
                    </form>

                    {formError && (
                        <p className="auth-feedback error" role="alert">
                            {formError}
                        </p>
                    )}

                    <div className="divider" aria-hidden="true">
                        <span>or continue with</span>
                    </div>

                    <div className="social-buttons">
                        <button
                            className="social-button"
                            type="button"
                            onClick={handleFacebookLogin}
                            disabled={
                                isSubmitting
                                || isFacebookSubmitting
                                || isGoogleSubmitting
                            }
                        >
                            <Image
                                className="social-icon"
                                src="/facebook.svg"
                                alt=""
                                width={22}
                                height={22}
                            />
                            <span>
                                {isFacebookSubmitting
                                    ? "Connecting..."
                                    : "Login with Facebook"}
                            </span>
                        </button>
                        <button
                            className="social-button"
                            type="button"
                            onClick={handleGoogleLogin}
                            disabled={
                                isSubmitting
                                || isFacebookSubmitting
                                || isGoogleSubmitting
                            }
                        >
                            <Image
                                className="social-icon"
                                src="/google.svg"
                                alt=""
                                width={22}
                                height={22}
                            />
                            <span>
                                {isGoogleSubmitting
                                    ? "Connecting..."
                                    : "Login with Google"}
                            </span>
                        </button>
                    </div>

                    <p className="signup-prompt">
                        Don&apos;t have an account?{" "}
                        <Link className="text-link" href="/signup">
                            Sign up
                        </Link>
                    </p>
                </div>
            </section>
        </main>
    );
}
