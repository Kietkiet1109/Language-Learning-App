import type { Metadata } from "next";
import Link from "next/link";
import Image from "next/image";

export const metadata: Metadata = {
    title: "Login | Prononcia",
    description: "Continue your pronunciation journey with Prononcia.",
};

export default function LoginPage() {
    return (
        <main className="login-page">
            <section className="login-card" aria-labelledby="login-title">
                <header className="login-header">
                    <span className="header-mark" aria-hidden="true">
                      P
                    </span>
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

                    <form className="login-form">
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
                              autoComplete="current-password"
                              placeholder="Enter your password"
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

                        <button className="primary-button" type="submit">
                          Log In
                        </button>
                    </form>

                    <div className="divider" aria-hidden="true">
                        <span>or continue with</span>
                    </div>

                    <div className="social-buttons">
                        <button className="social-button" type="button">
                            <Image
                              className="social-icon"
                              src="/facebook.svg"
                              alt=""
                              width={22}
                              height={22}
                            />
                            <span>Login with Facebook</span>
                        </button>
                        <button className="social-button" type="button">
                            <Image
                              className="social-icon"
                              src="/google.svg"
                              alt=""
                              width={22}
                              height={22}
                            />
                            <span>Login with Google</span>
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
