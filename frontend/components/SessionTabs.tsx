"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSessionStore } from "@/lib/sessionStore";

export default function SessionTabs() {
  const sessions = useSessionStore((s) => s.sessions);
  const activeId = useSessionStore((s) => s.activeId);
  const setActive = useSessionStore((s) => s.setActive);
  const removeSession = useSessionStore((s) => s.removeSession);
  const pathname = usePathname();
  const router = useRouter();

  return (
    <nav className="flex items-center gap-1 px-4 py-2 bg-gray-950 border-b border-gray-800 overflow-x-auto">
      <Link
        href="/"
        className={`px-3 py-1.5 text-sm rounded whitespace-nowrap ${
          pathname === "/" ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-800"
        }`}
      >
        + New
      </Link>
      {sessions.map((s) => {
        const active = pathname === "/session" && activeId === s.id;
        return (
          <div key={s.id} className="flex items-center">
            <button
              onClick={() => {
                setActive(s.id);
                router.push("/session");
              }}
              className={`pl-3 pr-2 py-1.5 text-sm rounded-l whitespace-nowrap ${
                active ? "bg-blue-600 text-white" : "text-gray-300 hover:bg-gray-800"
              }`}
              title={`${s.universe.join(", ")} vs ${s.benchmark}`}
            >
              {s.title}
            </button>
            <button
              onClick={(e) => {
                e.preventDefault();
                removeSession(s.id);
                if (active) router.push("/");
              }}
              className={`px-2 py-1.5 text-sm rounded-r ${
                active ? "bg-blue-600 text-white hover:bg-blue-500" : "text-gray-500 hover:bg-gray-800"
              }`}
              aria-label={`Close ${s.title}`}
            >
              ✕
            </button>
          </div>
        );
      })}
    </nav>
  );
}
