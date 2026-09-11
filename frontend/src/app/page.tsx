import Link from "next/link";

interface MenuOptionProps {
    href: string;
    label: string;
    description: string;
}

const MENU_OPTIONS: MenuOptionProps[] = [
    {
        href: "/learning",
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
    return (
        <main className="menu-page">
            <section className="menu-card" aria-labelledby="menu-title">
                <header className="menu-header">
                    <span className="header-mark" aria-hidden="true">
                        P
                    </span>
                    <h1 id="menu-title">Menu</h1>
                    <span className="header-spacer" aria-hidden="true" />
                </header>

                <nav aria-label="Main menu">
                    <ul className="menu-list">
                        {MENU_OPTIONS.map((option) => (
                            <MenuOption key={option.href} {...option} />
                        ))}
                    </ul>
                </nav>
            </section>
        </main>
    );
}
