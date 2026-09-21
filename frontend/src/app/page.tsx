"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CurrentUser, getCurrentUser, logoutUser } from "../lib/authApi";

interface MenuOptionProps {
    href?: string;
    label: string;
    description: string;
    isInDevelopment?: boolean;
}

const MENU_OPTIONS: MenuOptionProps[] = [
    {
        href: "/parselink",
        label: "Start Learning",
        description: "Begin a new pronunciation lesson",
    },
    {
        href: "/progress",
        label: "Progress (In Development)",
        description: "Review your learning history",
        isInDevelopment: true,
    },
    {
        href: "/profilesettings",
        label: "Profile Setting (In Development)",
        description: "Manage your profile preferences",
        isInDevelopment: true,
    },
    {
        href: "/notisettings",
        label: "Notification Setting (In Development)",
        description: "Choose when Prononcia can remind you",
        isInDevelopment: true,
    },
];

function MenuOption({
    href,
    label,
    description,
    isInDevelopment = false,
}: MenuOptionProps) {
    return (
        <li className="menu-item">
            {isInDevelopment ? (
                <button className="menu-option" type="button" disabled>
                    <span>{label}</span>
                    <span className="visually-hidden">{description}</span>
                    <span
                        className="info-button"
                        role="img"
                        aria-label={`More information about ${label}`}
                        title={description}
                    >
                        i
                    </span>
                </button>
            ) : (
                <Link className="menu-option" href={href ?? "/"}>
                    <span>{label}</span>
                    <span className="visually-hidden">{description}</span>
                    <span
                        className="info-button"
                        role="img"
                        aria-label={`More information about ${label}`}
                        title={description}
                    >
                        i
                    </span>
                </Link>
            )}
        </li>
    );
}

export default function Home() {
    const router = useRouter();
    const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
    const [isCheckingAuth, setIsCheckingAuth] = useState(true);
    const [isLoggingOut, setIsLoggingOut] = useState(false);

    useEffect(() => {
        let isMounted = true;

        const loadCurrentUser = async () => {
            try {
                const user = await getCurrentUser();

                if (isMounted) {
                    setCurrentUser(user);
                }
            } catch {
                if (isMounted) {
                    router.replace("/login");
                }
            } finally {
                if (isMounted) {
                    setIsCheckingAuth(false);
                }
            }
        };

        loadCurrentUser();

        return () => {
            isMounted = false;
        };
    }, [router]);

    const handleLogout = async () => {
        setIsLoggingOut(true);

        try {
            await logoutUser();
        } finally {
            router.replace("/login");
        }
    };

    if (isCheckingAuth || !currentUser) {
        return <main className="menu-page" aria-busy="true" />;
    }

    return (
        <main className="menu-page">
            <section className="menu-card" aria-labelledby="menu-title">
                <header className="menu-header">
                    <span className="header-mark" aria-hidden="true">
                        P
                    </span>
                    <h1 id="menu-title">Menu</h1>
                    <button
                        className="logout-button"
                        type="button"
                        onClick={handleLogout}
                        disabled={isLoggingOut}
                    >
                        {isLoggingOut ? "Logging out..." : "Logout"}
                    </button>
                </header>

                <div className="menu-content">
                    <div className="welcome-copy">
                        <p className="eyebrow">Hello, {currentUser.name}</p>
                        <p className="menu-description">
                            Practice today, speak more confidently tomorrow.
                        </p>
                    </div>

                    <nav aria-label="Main menu">
                        <ul className="menu-list">
                            {MENU_OPTIONS.map((option) => (
                                <MenuOption key={option.label} {...option} />
                            ))}
                        </ul>
                    </nav>
                </div>
            </section>
        </main>
    );
}
