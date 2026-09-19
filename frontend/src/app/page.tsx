"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CurrentUser, getCurrentUser, logoutUser } from "../lib/authApi";

interface MenuOptionProps {
    href: string;
    label: string;
    description: string;
}

const MENU_OPTIONS: MenuOptionProps[] = [
    {
        href: "/parselink",
        label: "Start Learning",
        description: "Begin a new pronunciation lesson",
    },
    {
        href: "/progress",
        label: "Progress",
        description: "Review your learning history",
    },
    {
        href: "/profilesettings",
        label: "Profile Setting",
        description: "Manage your profile preferences",
    },
    {
        href: "/notisettings",
        label: "Notification Setting",
        description: "Choose when Prononcia can remind you",
    },
];

function MenuOption({
    href,
    label,
    description,
}: MenuOptionProps) {
    return (
        <li className="menu-item">
            <Link className="menu-option" href={href}>
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
        </li>
    );
}

export default function Home() {
    const router = useRouter();
    const [currentUser, setCurrentUser] = useState<CurrentUser>({name: "Kiet",});
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
                // router.replace("/login");
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
                                <MenuOption key={option.href} {...option} />
                            ))}
                        </ul>
                    </nav>
                </div>
            </section>
        </main>
    );
}
