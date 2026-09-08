"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

const PASSWORD_PATTERN =
    "(?=.*[a-z])(?=.*[A-Z])(?=.*[^A-Za-z0-9]).{8,}";

export default function ResetPasswordPage() {
    const router = useRouter();
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [errorMessage, setErrorMessage] = useState("");
    const [isSuccess, setIsSuccess] = useState(false);
    const isPasswordMatch =
        confirmPassword.length > 0 && newPassword === confirmPassword;

        const passwordRules = [
        {
            label: "At least 8 characters",
            isMet: newPassword.length >= 8,
        },
        {
            label: "At least 1 uppercase letter",
            isMet: /[A-Z]/.test(newPassword),
        },
        {
            label: "At least 1 lowercase letter",
            isMet: /[a-z]/.test(newPassword),
        },
        {
            label: "At least 1 number",
            isMet: /[0-9]/.test(newPassword),
        },
        {
            label: "At least 1 symbol",
            isMet: /[^A-Za-z0-9]/.test(newPassword),
        },
    ];

    useEffect(() => {
        if (!isSuccess) {
            return;
        }

        const redirectTimer = window.setTimeout(() => {
            router.replace("/login");
        }, 1600);

        return () => window.clearTimeout(redirectTimer);
    }, [isSuccess, router]);

    const handleResetPassword = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();
        setErrorMessage("");

        if (newPassword.length < 8) {
            setErrorMessage(
                "Your new password must contain at least 8 characters.",
            );
            return;
        }

        if (newPassword !== confirmPassword) {
            setErrorMessage("The passwords do not match.");
            return;
        }

        setIsSuccess(true);
    };

    return (
        <main className="auth-page">
            {isSuccess && (
                <div className="success-popup" role="status">
                    Password reset successfully. Returning to login...
                </div>
            )}

            <section className="auth-card" aria-labelledby="reset-title">
                <header className="auth-header">
                    <span className="header-mark" aria-hidden="true">
                        P
                    </span>
                    <h1 id="reset-title">Reset Password</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <div className="auth-content">
                    <div className="welcome-copy">
                        <p className="eyebrow">Choose a new password</p>
                        <p className="auth-description">
                            Use a strong password that you do not use for
                            another account.
                        </p>
                    </div>

                    <form className="auth-form" onSubmit={handleResetPassword}>
                        <div className="form-field">
                            <label htmlFor="newPassword">New Password</label>
                            <input
                                id="newPassword"
                                name="newPassword"
                                type="password"
                                autoComplete="new-password"
                                placeholder="Enter a new password"
                                value={newPassword}
                                onChange={(event) => {
                                    setNewPassword(event.target.value);
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
                                Confirm New Password
                            </label>
                            <input
                                id="confirmPassword"
                                name="confirmPassword"
                                type="password"
                                autoComplete="new-password"
                                placeholder="Confirm your new password"
                                value={confirmPassword}
                                onChange={(event) => {
                                    setConfirmPassword(event.target.value);
                                }}
                                aria-invalid={
                                    confirmPassword.length > 0 &&
                                    !isPasswordMatch
                                }
                                required
                            />
                            {confirmPassword.length > 0 && (
                                <p
                                    className={
                                        isPasswordMatch
                                            ? "field-feedback success"
                                            : "field-feedback error"
                                    }
                                >
                                    {isPasswordMatch
                                        ? "Passwords match."
                                        : "Passwords do not match."}
                                </p>
                            )}
                        </div>

                        <button className="primary-button" type="submit">
                            Reset Password
                        </button>
                    </form>

                    {errorMessage && (
                        <p className="auth-feedback error" role="alert">
                            {errorMessage}
                        </p>
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
