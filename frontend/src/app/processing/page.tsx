"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

const PROCESSING_STAGES = [
    {
        maximum: 30,
        label: "Preparing video",
        detail: "Checking the video link",
    },
    {
        maximum: 65,
        label: "Extracting audio",
        detail: "Getting the audio ready for transcription",
    },
    {
        maximum: 100,
        label: "Extracting transcript",
        detail: "Organizing sentences for your lesson",
    },
];

function getProcessingStage(progress: number) {
    return (
        PROCESSING_STAGES.find((stage) => progress <= stage.maximum) ??
        PROCESSING_STAGES[PROCESSING_STAGES.length - 1]
    );
}

export default function ProcessingPage() {
    const router = useRouter();
    const [progress, setProgress] = useState(12);
    const [processingError, setProcessingError] = useState("");
    const processingStage = getProcessingStage(progress);

    useEffect(() => {
        const videoUrl = new URLSearchParams(window.location.search).get(
            "video"
        );

        if (!videoUrl) {
            setProcessingError("No video link was provided.");
            return undefined;
        }

        const processVideo = async () => {
            try {
                const apiUrl = process.env.NEXT_PUBLIC_API_URL ??
                    "http://localhost:8000";
                const response = await fetch(`${apiUrl}/process-video`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    credentials: "include",
                    body: JSON.stringify({ url: videoUrl }),
                });

                if (!response.ok) {
                    const errorBody = await response.json().catch(() => null);
                    throw new Error(
                        errorBody?.detail ?? "Video processing failed."
                    );
                }

                const processedVideo = await response.json();
                window.sessionStorage.setItem(
                    "prononcia.processedVideo",
                    JSON.stringify(processedVideo)
                );
                setProgress(100);
            } catch (error) {
                setProcessingError(
                    error instanceof Error
                        ? error.message
                        : "Video processing failed."
                );
            }
        };

        processVideo();

        const timer = window.setInterval(() => {
            setProgress((currentProgress) => {
                if (currentProgress >= 90) {
                    return currentProgress;
                }

                return Math.min(currentProgress + 2, 90);
            });
        }, 220);

        return () => window.clearInterval(timer);
    }, []);

    useEffect(() => {
        if (progress >= 100) {
            router.replace("/record");
        }
    }, [progress, router]);

    return (
        <main className="processing-page">
            <section
                className="processing-card"
                aria-labelledby="processing-title"
            >
                <header className="processing-header">
                    <Link
                        className="header-mark"
                        href="/parselink"
                        aria-label="Cancel processing and return to Start Learning"
                    >
                        <span aria-hidden="true">←</span>
                    </Link>
                    <h1 id="processing-title">Processing</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <div className="processing-content" aria-live="polite">
                    {processingError && (
                        <p className="form-error" role="alert">
                            {processingError}
                        </p>
                    )}

                    <div
                        className="processing-spinner"
                        role="status"
                        aria-label="Video processing in progress"
                    />

                    <div className="processing-message">
                        <p className="processing-label">
                            {processingStage.label}
                            <span aria-hidden="true">...</span>
                        </p>
                        <p className="processing-detail">
                            {processingStage.detail}
                        </p>
                    </div>

                    <div className="processing-progress-group">
                        <div className="processing-progress-heading">
                            <span>Lesson preparation</span>
                            <span>{progress}%</span>
                        </div>
                        <div
                            className="processing-progress-track"
                            role="progressbar"
                            aria-valuemin={0}
                            aria-valuemax={100}
                            aria-valuenow={progress}
                            aria-label="Lesson preparation progress"
                        >
                            <span
                                className="processing-progress-fill"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>

                    <p className="processing-note">
                        Keep this page open while we prepare your practice
                        sentences.
                    </p>
                </div>
            </section>
        </main>
    );
}
