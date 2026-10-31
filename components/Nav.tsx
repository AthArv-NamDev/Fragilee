import Link from "next/link";

export default function Nav() {
    return (
        <nav className="flex justify-between items-center px-14 py-7">
            <div className="bg-cream text-charcoal font-bold text-sm px-4 py-2 border-2 border-charcoal -rotate-2 inline-block">
                FRAGILEE™
            </div>
            <Link href="/login" className="border border-text text-text text-sm px-6 py-2 rounded-full">
                Log in
            </Link>
        </nav>
    );
}