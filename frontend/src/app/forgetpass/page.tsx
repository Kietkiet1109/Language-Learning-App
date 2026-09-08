"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const VERIFICATION_CODE = "123456";

type FeedbackState = {
    tone: "success" | "error";
    message: string;
} | null;

export default function ForgotPasswordPage() {
    const router = useRouter();
    const [email, setEmail] = useState("");
    const [verificationCode, setVerificationCode] = useState("");
    const [hasRequestedCode, setHasRequestedCode] = useState(false);
    const [resendCountdown, setResendCountdown] = useState(0);
    const [feedback, setFeedback] = useState<FeedbackState>(null);
    const sendButtonLabel = hasRequestedCode
        ? "Resend Email"
        : "Send Email";

    useEffect(() => {
        if (resendCountdown === 0) {
            return;
        }

        const countdownTimer = window.setInterval(() => {
            setResendCountdown((currentCountdown) => currentCountdown - 1);
        }, 1000);

        return () => window.clearInterval(countdownTimer);
    }, [resendCountdown]);

    const handleSendEmail = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (resendCountdown > 0) {
            return;
        }

        const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

        if (!emailPattern.test(email.trim())) {
            setFeedback({
                tone: "error",
                message: "Please enter a valid email address.",
            });
            return;
        }

        setFeedback({
            tone: "success",
            message:
                "Verification email sent.",
        });
        setHasRequestedCode(true);
        setResendCountdown(30);
    };

    const handleVerifyCode = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (!hasRequestedCode) {
            setFeedback({
                tone: "error",
                message: "Request a verification code before verifying.",
            });
            return;
        }

        if (verificationCode !== VERIFICATION_CODE) {
            setFeedback({
                tone: "error",
                message: "The verification code is invalid.",
            });
            return;
        }

        router.push("/resetpass");
    };

    return (
        <main className="auth-page">
            <section className="auth-card" aria-labelledby="forgot-title">
                <header className="auth-header">
                    <span className="header-mark" aria-hidden="true">
                        P
                    </span>
                    <h1 id="forgot-title">Forgot Password</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <div className="auth-content">
                    <div className="welcome-copy">
                        <p className="eyebrow">Account recovery</p>
                        <p className="auth-description">
                            Enter your email to receive a verification code and
                            reset your Prononcia password.
                        </p>
                    </div>

                    <form className="auth-form" onSubmit={handleSendEmail}>
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
                                }}
                                required
                            />
                        </div>

                        <button
                            className="primary-button"
                            type="submit"
                            disabled={resendCountdown > 0}
                        >
                            {resendCountdown > 0
                                ? `Resend in ${resendCountdown}s`
                                : sendButtonLabel}
                        </button>
                    </form>

                    {feedback && (
                        <p
                            className={`auth-feedback ${feedback.tone}`}
                            role={
                                feedback.tone === "error" ? "alert" : "status"
                            }
                        >
                            {feedback.message}
                        </p>
                    )}

                    {hasRequestedCode && (
                        <form
                            className="auth-form"
                            onSubmit={handleVerifyCode}
                        >
                            <div className="form-field">
                                <label htmlFor="verificationCode">
                                    Verification Code
                                </label>
                                <input
                                    id="verificationCode"
                                    name="verificationCode"
                                    type="text"
                                    inputMode="numeric"
                                    autoComplete="one-time-code"
                                    placeholder="Enter your code"
                                    value={verificationCode}
                                    onChange={(event) => {
                                        setVerificationCode(
                                            event.target.value,
                                        );
                                    }}
                                    maxLength={6}
                                    required
                                />
                            </div>

                            <button
                                className="primary-button"
                                type="submit"
                            >
                                Verify Code
                            </button>
                        </form>
                    )}

                    <p className="auth-secondary-action">
                        <Link className="text-link" href="/login">
                            Return to login
                        </Link>
                    </p>
                </div>
            </section>
        </main>
    );
}
