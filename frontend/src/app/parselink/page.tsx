"use client";

import { FormEvent, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

function isYouTubeUrl(value: string) {
    try {
        const url = new URL(value);
        const hostname = url.hostname.toLowerCase();
        const isYouTubeHost = [
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
            "youtu.be",
            "www.youtu.be",
        ].includes(hostname);

        if (!isYouTubeHost) {
            return false;
        }

        if (hostname.includes("youtu.be")) {
            return Boolean(url.pathname.slice(1));
        }

        return Boolean(
            url.searchParams.get("v") ||
                /\/(shorts|embed|live)\/[^/]+/.test(url.pathname)
        );
    } catch {
        return false;
    }
}

export default function LearningPage() {
    const router = useRouter();
    const [videoLink, setVideoLink] = useState("");
    const [formError, setFormError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        const normalizedVideoLink = videoLink.trim();
        if (!normalizedVideoLink) {
            setFormError("Please enter a YouTube video link to continue.");
            return;
        }

        if (!isYouTubeUrl(normalizedVideoLink)) {
            setFormError("Please enter a valid YouTube video link.");
            return;
        }

        setFormError("");
        setIsSubmitting(true);
        router.push(
            `/processing?video=${encodeURIComponent(normalizedVideoLink)}`
        );
    };

    return (
        <main className="learning-page">
            <section
                className="learning-card"
                aria-labelledby="learning-title"
            >
                <header className="learning-header">
                    <Link
                        className="header-mark"
                        href="/"
                        aria-label="Return to Main Page"
                    >
                        <span aria-hidden="true">←</span>
                    </Link>
                    <h1>Start Learning</h1>
                    <span aria-hidden="true" />
                </header>

                <form className="learning-form" onSubmit={handleSubmit}>
                    <div className="learning-intro">
                        <h2 id="learning-title">
                            Enter YouTube
                            <br />
                            Video Link
                        </h2>
                        <p>
                            Paste a video link to begin your pronunciation
                            practice.
                        </p>
                    </div>

                    <label className="visually-hidden" htmlFor="video-link">
                        YouTube video link
                    </label>
                    <input
                        id="video-link"
                        name="videoLink"
                        type="url"
                        value={videoLink}
                        onChange={(event) => {
                            setVideoLink(event.target.value);
                            setFormError("");
                        }}
                        placeholder="https://www.youtube.com/..."
                        aria-describedby={
                            formError ? "video-link-error" : undefined
                        }
                    />

                    {formError && (
                        <p
                            className="form-error"
                            id="video-link-error"
                            role="alert"
                        >
                            {formError}
                        </p>
                    )}

                    <button
                        type="submit"
                        className="learning-button"
                        disabled={isSubmitting}
                    >
                        {isSubmitting ? "Preparing..." : "Start Learning"}
                    </button>
                </form>
            </section>
        </main>
    );
}
