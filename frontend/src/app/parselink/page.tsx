"use client";

import { FormEvent, useState } from "react";

export default function LearningPage() {
    const [videoLink, setVideoLink] = useState("");
    const [formError, setFormError] = useState("");

    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
        event.preventDefault();

        if (!videoLink.trim()) {
            setFormError("Please enter a YouTube video link to continue.");
            return;
        }

        setFormError("");
    };

    return (
        <main className="learning-page">
            <section
                className="learning-card"
                aria-labelledby="learning-title"
            >
                <header className="learning-header">
                    <span className="header-mark" aria-hidden="true">
                        P
                    </span>
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

                    <button type="submit" className="learning-button">
                        Start Learning
                    </button>
                </form>
            </section>
        </main>
    );
}
