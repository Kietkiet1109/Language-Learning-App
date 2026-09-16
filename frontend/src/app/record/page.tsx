"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";

interface TranscriptSegment {
    sequence_number: number;
    start_seconds: number;
    end_seconds: number;
    french: string;
    english: string | null;
}

interface VideoPart {
    part_number: 1 | 2 | 3;
    mode: "listening" | "repeat_and_evaluate" | "audio_only";
    title: string;
    start_seconds: number;
    end_seconds: number;
    show_transcript: boolean;
    pause_after_segment: boolean;
    record_audio: boolean;
    show_translation: boolean;
    segments: TranscriptSegment[];
}

interface VideoPartsResponse {
    video_id: string;
    source_url: string;
    parts: VideoPart[];
}

interface StoredVideo {
    video_id?: string;
}

interface YouTubePlayer {
    destroy: () => void;
    getCurrentTime: () => number;
    getPlayerState: () => number;
    pauseVideo: () => void;
    playVideo: () => void;
    seekTo: (seconds: number, allowSeekAhead: boolean) => void;
}

interface YouTubeNamespace {
    Player: new (
        element: HTMLElement,
        options: {
            videoId: string;
            playerVars: Record<string, number>;
            events: {
                onReady: (event: { target: YouTubePlayer }) => void;
            };
        }
    ) => YouTubePlayer;
}

declare global {
    interface Window {
        YT?: YouTubeNamespace;
        onYouTubeIframeAPIReady?: () => void;
    }
}

const YOUTUBE_IFRAME_API = "https://www.youtube.com/iframe_api";
const YOUTUBE_PLAYING_STATE = 1;

function loadYouTubeApi() {
    if (window.YT?.Player) {
        return Promise.resolve(window.YT);
    }

    return new Promise<YouTubeNamespace>((resolve, reject) => {
        const existingScript = document.querySelector(
            `script[src="${YOUTUBE_IFRAME_API}"]`
        );
        const previousCallback = window.onYouTubeIframeAPIReady;

        window.onYouTubeIframeAPIReady = () => {
            previousCallback?.();

            if (window.YT?.Player) {
                resolve(window.YT);
                return;
            }

            reject(new Error("The YouTube player could not be loaded."));
        };

        if (existingScript) {
            return;
        }

        const script = document.createElement("script");
        script.src = YOUTUBE_IFRAME_API;
        script.async = true;
        script.onerror = () => {
            reject(new Error("The YouTube player could not be loaded."));
        };
        document.body.appendChild(script);
    });
}

function MicrophoneIcon() {
    return (
        <svg
            aria-hidden="true"
            className="microphone-icon"
            viewBox="0 0 32 32"
        >
            <rect x="11" y="4" width="10" height="17" rx="5" />
            <path d="M7 15a9 9 0 0 0 18 0M16 24v4M11 28h10" />
        </svg>
    );
}

function PlayIcon() {
    return (
        <svg aria-hidden="true" className="play-icon" viewBox="0 0 42 42">
            <path d="M14 8v26l21-13L14 8Z" />
        </svg>
    );
}

function PauseIcon() {
    return (
        <svg aria-hidden="true" className="pause-icon" viewBox="0 0 42 42">
            <path d="M12 8h7v26h-7zM23 8h7v26h-7z" />
        </svg>
    );
}

export default function RecordPage() {
    const router = useRouter();
    const playerMountRef = useRef<HTMLDivElement>(null);
    const playerRef = useRef<YouTubePlayer | null>(null);
    const [videoId, setVideoId] = useState("");
    const [parts, setParts] = useState<VideoPartsResponse | null>(null);
    const [sentenceIndex, setSentenceIndex] = useState(0);
    const [isLoading, setIsLoading] = useState(true);
    const [loadError, setLoadError] = useState("");
    const [isPlayerReady, setIsPlayerReady] = useState(false);
    const [isVideoPlaying, setIsVideoPlaying] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [hasResult, setHasResult] = useState(false);

    const repeatPart = parts?.parts.find(
        (part) => part.part_number === 2
    );
    const sentences = repeatPart?.segments ?? [];
    const sentence = sentences[sentenceIndex];
    const isFirstSentence = sentenceIndex === 0;
    const isLastSentence = sentenceIndex === sentences.length - 1;

    useEffect(() => {
        let isCancelled = false;
        const abortController = new AbortController();

        const loadParts = async () => {
            try {
                const storedValue = window.sessionStorage.getItem(
                    "prononcia.processedVideo"
                );
                const storedVideo = storedValue
                    ? (JSON.parse(storedValue) as StoredVideo)
                    : null;
                const storedVideoId = storedVideo?.video_id;

                if (!storedVideoId) {
                    throw new Error(
                        "The processed video could not be identified."
                    );
                }

                setVideoId(storedVideoId);
                const apiUrl = process.env.NEXT_PUBLIC_API_URL ??
                    "http://localhost:8000";
                const response = await fetch(
                    `${apiUrl}/video/${encodeURIComponent(
                        storedVideoId
                    )}/parts`,
                    {
                        credentials: "include",
                        signal: abortController.signal,
                    }
                );
                const responseBody = await response.json();

                if (!response.ok) {
                    throw new Error(
                        responseBody?.detail ??
                            "The lesson transcript could not be loaded."
                    );
                }

                if (!isCancelled) {
                    setParts(responseBody as VideoPartsResponse);
                }
            } catch (error) {
                if (!isCancelled && !abortController.signal.aborted) {
                    setLoadError(
                        error instanceof Error
                            ? error.message
                            : "The lesson could not be loaded."
                    );
                }
            } finally {
                if (!isCancelled) {
                    setIsLoading(false);
                }
            }
        };

        loadParts();

        return () => {
            isCancelled = true;
            abortController.abort();
        };
    }, []);

    useEffect(() => {
        if (isLoading || !videoId || !playerMountRef.current) {
            return undefined;
        }

        let isCancelled = false;

        loadYouTubeApi()
            .then((youtube) => {
                if (isCancelled || !playerMountRef.current) {
                    return;
                }

                playerRef.current = new youtube.Player(
                    playerMountRef.current,
                    {
                        videoId,
                        playerVars: {
                            controls: 0,
                            modestbranding: 1,
                            playsinline: 1,
                            rel: 0,
                        },
                        events: {
                            onReady: ({ target }) => {
                                playerRef.current = target;
                                setIsPlayerReady(true);
                            },
                        },
                    }
                );
            })
            .catch((error: unknown) => {
                if (!isCancelled) {
                    setLoadError(
                        error instanceof Error
                            ? error.message
                            : "The YouTube player could not be loaded."
                    );
                }
            });

        return () => {
            isCancelled = true;
            playerRef.current?.destroy();
            playerRef.current = null;
            setIsPlayerReady(false);
        };
    }, [isLoading, videoId]);

    useEffect(() => {
        if (!isPlayerReady || !sentence || !playerRef.current) {
            return undefined;
        }

        playerRef.current.pauseVideo();
        playerRef.current.seekTo(sentence.start_seconds, true);
        setIsVideoPlaying(false);

        const timer = window.setInterval(() => {
            const player = playerRef.current;
            if (!player || player.getPlayerState() !== YOUTUBE_PLAYING_STATE) {
                return;
            }

            if (player.getCurrentTime() >= sentence.end_seconds) {
                player.seekTo(sentence.start_seconds, true);
                player.playVideo();
            }
        }, 100);

        return () => window.clearInterval(timer);
    }, [isPlayerReady, sentence?.start_seconds, sentence?.end_seconds]);

    useEffect(() => {
        if (!isRecording) {
            return undefined;
        }

        const timer = window.setTimeout(() => {
            setIsRecording(false);
            setHasResult(true);
        }, 1100);

        return () => window.clearTimeout(timer);
    }, [isRecording]);

    const handleVideoToggle = () => {
        const player = playerRef.current;
        if (!player || !sentence) {
            return;
        }

        if (player.getPlayerState() === YOUTUBE_PLAYING_STATE) {
            player.pauseVideo();
            setIsVideoPlaying(false);
            return;
        }

        const currentTime = player.getCurrentTime();
        if (
            currentTime < sentence.start_seconds ||
            currentTime >= sentence.end_seconds
        ) {
            player.seekTo(sentence.start_seconds, true);
        }
        player.playVideo();
        setIsVideoPlaying(true);
    };

    const handleRecord = () => {
        setHasResult(false);
        setIsRecording(true);
    };

    const handleRetry = () => {
        setHasResult(false);
    };

    const handlePrevious = () => {
        setSentenceIndex((currentIndex) => Math.max(currentIndex - 1, 0));
        setHasResult(false);
        setIsRecording(false);
    };

    const handleNext = () => {
        setSentenceIndex((currentIndex) =>
            Math.min(currentIndex + 1, sentences.length - 1)
        );
        setHasResult(false);
        setIsRecording(false);
    };

    const handleDone = () => {
        router.push("/result");
    };

    if (isLoading) {
        return (
            <main className="record-page">
                <section className="record-card record-state-card">
                    <div className="record-state" role="status">
                        Loading your practice sentences...
                    </div>
                </section>
            </main>
        );
    }

    if (loadError || !parts || !sentence) {
        return (
            <main className="record-page">
                <section className="record-card record-state-card">
                    <div className="record-state">
                        <p className="form-error" role="alert">
                            {loadError || "No practice sentences were found."}
                        </p>
                        <Link className="primary-action" href="/parselink">
                            Return to Start Learning
                        </Link>
                    </div>
                </section>
            </main>
        );
    }

    return (
        <main className="record-page">
            <section className="record-card" aria-labelledby="record-title">
                <header className="record-header">
                    <Link
                        className="header-mark"
                        href="/parselink"
                        aria-label="Return to Start Learning"
                    >
                        <span aria-hidden="true">←</span>
                    </Link>
                    <h1 id="record-title">Repeat and evaluate</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <div className="record-content">
                    <div className="video-preview" aria-label="Video preview">
                        <div
                            className="youtube-player"
                            ref={playerMountRef}
                            aria-hidden="true"
                        />
                        <button
                            className="video-toggle"
                            type="button"
                            onClick={handleVideoToggle}
                            disabled={!isPlayerReady}
                            aria-label={
                                isVideoPlaying
                                    ? "Pause sentence video"
                                    : "Play sentence video"
                            }
                        >
                            <span className="video-play-button">
                                {isVideoPlaying ? <PauseIcon /> : <PlayIcon />}
                            </span>
                        </button>
                        <div className="video-controls" aria-hidden="true">
                            <span className="video-control-icon">
                                {isVideoPlaying ? "▮▮" : "▶"}
                            </span>
                            <span className="video-seek-track">
                                <span />
                            </span>
                            <span>
                                {Math.round(sentence.start_seconds)}s–
                                {Math.round(sentence.end_seconds)}s
                            </span>
                        </div>
                    </div>

                    <div className="sentence-panel">
                        <p className="sentence-label">
                            Sentence {sentenceIndex + 1} of {sentences.length}
                        </p>
                        <p className="sentence-text">{sentence.french}</p>
                        <p className="sentence-translation">
                            {sentence.english ??
                                "English translation is not available yet."}
                        </p>
                    </div>

                    {!hasResult && (
                        <div className="record-prompt" aria-live="polite">
                            <p>
                                {isRecording
                                    ? "Listening..."
                                    : "Repeat after this sentence"}
                            </p>
                            <button
                                className={`microphone-button ${
                                    isRecording ? "is-recording" : ""
                                }`}
                                type="button"
                                onClick={handleRecord}
                                disabled={isRecording}
                                aria-label={
                                    isRecording
                                        ? "Recording in progress"
                                        : "Record your pronunciation"
                                }
                            >
                                <MicrophoneIcon />
                            </button>
                            <span className="record-hint">
                                {isRecording
                                    ? "Speak clearly into your microphone"
                                    : "Tap to record"}
                            </span>
                        </div>
                    )}

                    {hasResult && (
                        <div className="record-result" aria-live="polite">
                            <p className="result-label">Recording captured</p>
                            <p className="result-words">
                                Your pronunciation is ready for evaluation.
                            </p>
                            <p className="result-feedback">
                                Pronunciation scoring will be connected to the
                                evaluation endpoint next.
                            </p>
                        </div>
                    )}

                    <nav
                        className="record-navigation"
                        aria-label="Sentence navigation"
                    >
                        {!hasResult && !isFirstSentence && (
                            <button
                                className="secondary-action"
                                type="button"
                                onClick={handlePrevious}
                            >
                                <span aria-hidden="true">←</span>
                                Previous
                            </button>
                        )}

                        {hasResult && (
                            <button
                                className="secondary-action"
                                type="button"
                                onClick={handleRetry}
                            >
                                Retry
                            </button>
                        )}

                        {!isLastSentence && (
                            <button
                                className="primary-action"
                                type="button"
                                onClick={handleNext}
                            >
                                Next
                                <span aria-hidden="true">→</span>
                            </button>
                        )}

                        {isLastSentence && (
                            <button
                                className="primary-action"
                                type="button"
                                onClick={handleDone}
                            >
                                Done
                                <span aria-hidden="true">✓</span>
                            </button>
                        )}
                    </nav>
                </div>
            </section>
        </main>
    );
}
