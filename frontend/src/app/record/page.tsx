"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

interface Sentence {
    french: string;
    english: string;
    sampleResponse: string;
    score: number;
}

const SENTENCES: Sentence[] = [
    {
        french: "Il fait chaud aujourd’hui.",
        english: "It is hot today.",
        sampleResponse: "Bonjour",
        score: 96,
    },
    {
        french: "Je voudrais pratiquer le français.",
        english: "I would like to practise French.",
        sampleResponse: "Je voudrais pratiquer le français",
        score: 91,
    },
    {
        french: "Nous allons apprendre ensemble.",
        english: "We are going to learn together.",
        sampleResponse: "Nous allons apprendre ensemble",
        score: 94,
    },
];

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

export default function RecordPage() {
    const router = useRouter();
    const [sentenceIndex, setSentenceIndex] = useState(0);
    const [isRecording, setIsRecording] = useState(false);
    const [hasResult, setHasResult] = useState(false);

    const sentence = SENTENCES[sentenceIndex];
    const isFirstSentence = sentenceIndex === 0;
    const isLastSentence = sentenceIndex === SENTENCES.length - 1;

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
            Math.min(currentIndex + 1, SENTENCES.length - 1)
        );
        setHasResult(false);
        setIsRecording(false);
    };

    const handleDone = () => {
        router.push("/result");
    };

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
                        <button
                            className="video-play-button"
                            type="button"
                            aria-label="Play video preview"
                        >
                            <PlayIcon />
                        </button>
                        <div className="video-controls" aria-hidden="true">
                            <span className="video-control-icon">▮◀</span>
                            <span className="video-seek-track">
                                <span />
                            </span>
                            <span>00%</span>
                        </div>
                    </div>

                    <div className="sentence-panel">
                        <p className="sentence-label">
                            Sentence {sentenceIndex + 1} of {SENTENCES.length}
                        </p>
                        <p className="sentence-text">{sentence.french}</p>
                        <p className="sentence-translation">
                            {sentence.english}
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
                            <p className="result-label">You said</p>
                            <p className="result-words">
                                “{sentence.sampleResponse}”
                            </p>
                            <p className="result-score">
                                {sentence.score}%
                            </p>
                            <p className="result-feedback">
                                Great work. Keep practising your rhythm.
                            </p>
                        </div>
                    )}

                    <nav className="record-navigation" aria-label="Sentence navigation">
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
                                disabled={!hasResult}
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
                                disabled={!hasResult}
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
