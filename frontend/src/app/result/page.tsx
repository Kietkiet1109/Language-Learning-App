"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getApiUrl } from "../../lib/api";

interface StoredVideo {
    video_id?: string;
    media_source_id?: string;
}

interface SaveResultResponse {
    video_id: string;
    overall_score: number;
    feedback: string;
    sentence_count: number;
    recorded_sentence_count: number;
    unrecorded_sentence_count: number;
}

export default function ResultPage() {
    const router = useRouter();
    const [result, setResult] = useState<SaveResultResponse | null>(null);
    const [errorMessage, setErrorMessage] = useState("");
    const [isLoading, setIsLoading] = useState(true);

    useEffect(() => {
        const abortController = new AbortController();

        const saveResult = async () => {
            try {
                const storedValue = window.sessionStorage.getItem(
                    "prononcia.processedVideo"
                );
                const storedVideo = storedValue
                    ? (JSON.parse(storedValue) as StoredVideo)
                    : null;

                const lessonId = storedVideo?.media_source_id ??
                    storedVideo?.video_id;
                if (!lessonId) {
                    throw new Error(
                        "The completed practice lesson could not be found."
                    );
                }

                const response = await fetch(getApiUrl("/save-result"), {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({
                        video_id: lessonId,
                    }),
                    credentials: "include",
                    signal: abortController.signal,
                });
                const responseBody = await response.json();

                if (!response.ok) {
                    throw new Error(
                        responseBody?.detail ??
                            "The practice result could not be saved."
                    );
                }

                setResult(responseBody as SaveResultResponse);
            } catch (error) {
                if (!abortController.signal.aborted) {
                    setErrorMessage(
                        error instanceof Error
                            ? error.message
                            : "The practice result could not be saved."
                    );
                }
            } finally {
                if (!abortController.signal.aborted) {
                    setIsLoading(false);
                }
            }
        };

        void saveResult();

        return () => abortController.abort();
    }, []);

    const handleFinishSession = () => {
        window.sessionStorage.removeItem("prononcia.processedVideo");
        router.push("/parselink");
    };

    if (isLoading) {
        return (
            <main className="result-page">
                <section className="result-card result-state-card">
                    <p role="status">Saving your practice result...</p>
                </section>
            </main>
        );
    }

    if (errorMessage || !result) {
        return (
            <main className="result-page">
                <section className="result-card result-state-card">
                    <header className="result-header">
                        <span className="header-mark" aria-hidden="true">
                            P
                        </span>
                        <h1 id="result-title">
                            Pronunciation
                            <br />
                            Feedback
                        </h1>
                    </header>
                    <span className="header-spacer" aria-hidden="true" />
                    <p className="form-error" role="alert">
                        {errorMessage || "No result was available."}
                    </p>
                    <button
                        className="result-finish-button"
                        type="button"
                        onClick={handleFinishSession}
                    >
                        Finish Session
                    </button>
                </section>
            </main>
        );
    }

    return (
        <main className="result-page">
            <section
                className="result-card result-feedback-card"
                aria-labelledby="result-title"
            >
                <header className="result-header">
                    <span className="header-mark" aria-hidden="true">
                        P
                    </span>
                    <h1 id="result-title">
                        Pronunciation
                        <br />
                        Feedback
                    </h1>
                </header>
                <span className="header-spacer" aria-hidden="true" />

                <div
                    className="result-score-circle"
                    aria-label={`Overall score ${result.overall_score}%`}
                >
                    <span>{result.overall_score}</span>
                    <small>%</small>
                </div>

                <p className="result-overall-feedback">{result.feedback}</p>

                <button
                    className="result-finish-button"
                    type="button"
                    onClick={handleFinishSession}
                >
                    Finish Session
                </button>
            </section>
        </main>
    );
}
