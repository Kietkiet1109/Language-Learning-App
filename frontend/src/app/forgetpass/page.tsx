"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
    requestPasswordReset,
    verifyPasswordReset,
} from "@/lib/authApi";

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
    const [isSending, setIsSending] = useState(false);
    const [isVerifying, setIsVerifying] = useState(false);
    const sendButtonLabel = hasRequestedCode
        ? "Resend Email"
        : "Send Email";
    let sendButtonText = sendButtonLabel;
    if (isSending) {
        sendButtonText = "Sending...";
    } else if (resendCountdown > 0) {
        sendButtonText = `Resend in ${resendCountdown}s`;
    }

    useEffect(() => {
        if (resendCountdown === 0) {
            return;
        }

        const countdownTimer = window.setInterval(() => {
            setResendCountdown((currentCountdown) => currentCountdown - 1);
        }, 1000);

        return () => window.clearInterval(countdownTimer);
    }, [resendCountdown]);

    const handleSendEmail = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (resendCountdown > 0) {
            return;
        }

        setFeedback(null);
        setIsSending(true);

        try {
            await requestPasswordReset(email.trim());
            setHasRequestedCode(true);
            setVerificationCode("");
            setResendCountdown(30);
            setFeedback({
                tone: "success",
                message: "Verification email sent.",
            });
        } catch (error) {
            setFeedback({
                tone: "error",
                message:
                    error instanceof Error
                        ? error.message
                        : "Unable to send the verification email.",
            });
        } finally {
            setIsSending(false);
        }
    };

    const handleVerifyCode = async (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setFeedback(null);
        setIsVerifying(true);

        try {
            const result = await verifyPasswordReset(
                email.trim(),
                verificationCode,
            );
            const encodedToken = encodeURIComponent(result.reset_token);
            router.push(`/resetpass?token=${encodedToken}`);
        } catch (error) {
            setFeedback({
                tone: "error",
                message:
                    error instanceof Error
                        ? error.message
                        : "The verification code is invalid or expired.",
            });
        } finally {
            setIsVerifying(false);
        }
    };

    return (
        <main className="auth-page">
            <section className="auth-card" aria-labelledby="forgot-title">
                <header className="auth-header">
                    <span className="header-mark" aria-hidden="true">P</span>
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
                                    setFeedback(null);
                                }}
                                required
                            />
                        </div>

                        <button
                            className="primary-button"
                            type="submit"
                            disabled={isSending || resendCountdown > 0}
                        >
                            {sendButtonText}
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
                                    placeholder="Enter your 6-digit code"
                                    value={verificationCode}
                                    onChange={(event) => {
                                        setVerificationCode(
                                            event.target.value.replace(
                                                /\D/g,
                                                "",
                                            ),
                                        );
                                        setFeedback(null);
                                    }}
                                    pattern="[0-9]{6}"
                                    maxLength={6}
                                    required
                                />
                            </div>

                            <button
                                className="primary-button"
                                type="submit"
                                disabled={
                                    isVerifying
                                    || verificationCode.length !== 6
                                }
                            >
                                {isVerifying ? "Verifying..." : "Verify Code"}
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
