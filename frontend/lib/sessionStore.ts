"use client";
import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { Session } from "./types";

interface SessionState {
  sessions: Session[];
  activeId: string | null;
  createSession: (partial: Omit<Session, "id" | "createdAt">) => string;
  updateSession: (id: string, patch: Partial<Session>) => void;
  removeSession: (id: string) => void;
  setActive: (id: string | null) => void;
  getSession: (id: string) => Session | undefined;
}

function genId(): string {
  return Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set, get) => ({
      sessions: [],
      activeId: null,
      createSession: (partial) => {
        const id = genId();
        const session: Session = { id, createdAt: Date.now(), ...partial };
        set((s) => ({ sessions: [...s.sessions, session], activeId: id }));
        return id;
      },
      updateSession: (id, patch) =>
        set((s) => ({
          sessions: s.sessions.map((x) => (x.id === id ? { ...x, ...patch } : x)),
        })),
      removeSession: (id) =>
        set((s) => {
          const sessions = s.sessions.filter((x) => x.id !== id);
          const activeId = s.activeId === id ? sessions[0]?.id ?? null : s.activeId;
          return { sessions, activeId };
        }),
      setActive: (id) => set({ activeId: id }),
      getSession: (id) => get().sessions.find((s) => s.id === id),
    }),
    {
      name: "rrg-sessions",
      storage: createJSONStorage(() => localStorage),
      version: 1,
    }
  )
);
