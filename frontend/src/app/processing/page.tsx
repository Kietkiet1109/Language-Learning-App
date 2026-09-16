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
    const [progress, setProgress] = useState(0);
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

        let isCancelled = false;
        const abortController = new AbortController();

        const apiUrl = process.env.NEXT_PUBLIC_API_URL ??
            "http://localhost:8000";

        const saveCompletedVideo = (processedVideo: unknown) => {
            if (isCancelled) {
                return;
            }

            window.sessionStorage.setItem(
                "prononcia.processedVideo",
                JSON.stringify(processedVideo)
            );
            setProgress(100);
        };

        const waitForProcessingJob = async (jobId: string) => {
            while (!isCancelled) {
                await new Promise((resolve) => {
                    window.setTimeout(resolve, 1200);
                });

                if (isCancelled) {
                    return;
                }

                const response = await fetch(
                    `${apiUrl}/process-video/${jobId}`,
                    {
                        credentials: "include",
                        signal: abortController.signal,
                    }
                );
                const processedVideo = await response.json();

                if (!response.ok) {
                    throw new Error(
                        processedVideo?.detail ??
                            "Video processing failed."
                    );
                }

                if (processedVideo.processing_status === "failed") {
                    throw new Error("Video processing failed.");
                }

                if (processedVideo.processing_status === "ready") {
                    saveCompletedVideo(processedVideo);
                    return;
                }
            }
        };

        const processVideo = async () => {
            try {
                const response = await fetch(`${apiUrl}/process-video`, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    credentials: "include",
                    signal: abortController.signal,
                    body: JSON.stringify({ url: videoUrl }),
                });

                if (!response.ok) {
                    const errorBody = await response.json().catch(() => null);
                    throw new Error(
                        errorBody?.detail ?? "Video processing failed."
                    );
                }

                const processedVideo = await response.json();
                if (processedVideo.processing_status === "ready") {
                    saveCompletedVideo(processedVideo);
                    return;
                }

                if (processedVideo.processing_status === "processing") {
                    await waitForProcessingJob(
                        processedVideo.processing_job_id
                    );
                    return;
                }

                throw new Error("Video processing failed.");
            } catch (error) {
                if (!isCancelled) {
                    setProcessingError(
                        error instanceof Error
                            ? error.message
                            : "Video processing failed."
                    );
                }
            }
        };

        processVideo();

        const timer = window.setInterval(() => {
            setProgress((currentProgress) => {
                if (currentProgress >= 99) {
                    return currentProgress;
                }

                return Math.min(currentProgress + 1, 99);
            });
        }, 220);

        return () => {
            isCancelled = true;
            abortController.abort();
            window.clearInterval(timer);
        };
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
