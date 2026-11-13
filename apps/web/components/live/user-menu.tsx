"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";

import { signOut } from "@/app/auth/actions";

export type UserMenuMode = "prod" | "public" | "mock";

function initialsFor(name: string, email?: string): string {
  const source = name.trim() || email?.split("@")[0] || "Account";
  const letters = source
    .replace(/[^\p{L}\p{N}]+/gu, " ")
    .trim()
    .split(/\s+/)
    .map((part) => part[0])
    .join("");
  return (letters.slice(0, 2) || "A").toUpperCase();
}

export function UserMenu({
  mode,
  name = "",
  email,
}: {
  mode: UserMenuMode;
  name?: string;
  email?: string;
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onPointerDown(event: PointerEvent) {
      if (!rootRef.current?.contains(event.target as Node)) setOpen(false);
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        triggerRef.current?.focus();
      }
    }
    document.addEventListener("pointerdown", onPointerDown);
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("pointerdown", onPointerDown);
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open]);

  if (mode === "public") {
    return (
      <span className="public-view">
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.8"
          aria-hidden="true"
        >
          <circle cx="12" cy="12" r="9" />
          <path d="M3 12h18M12 3a15 15 0 0 1 0 18M12 3a15 15 0 0 0 0 18" />
        </svg>
        Public view
      </span>
    );
  }

  const displayName = name.trim() || email?.split("@")[0] || "Account";
  const settingsHref = mode === "mock" ? "/?view=settings" : "/live/settings";
  const accountHref = mode === "mock" ? "/?view=settings" : "/live/settings#account";

  return (
    <div className="user-menu" ref={rootRef}>
      <button
        ref={triggerRef}
        className="user-menu-trigger"
        type="button"
        aria-expanded={open}
        aria-controls="user-menu-panel"
        onClick={() => setOpen((value) => !value)}
      >
        <span className="avatar">{initialsFor(displayName, email)}</span>
        <span className="uname">{displayName}</span>
        <svg
          className="user-menu-chevron"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden="true"
        >
          <path d="m6 9 6 6 6-6" />
        </svg>
      </button>

      <div className="user-menu-panel" id="user-menu-panel" hidden={!open}>
        <div className="user-menu-head">
          <b>{displayName}</b>
          {email ? <span>{email}</span> : null}
        </div>
        <Link className="user-menu-link" href={accountHref} onClick={() => setOpen(false)}>
          Account details
        </Link>
        <Link className="user-menu-link" href={settingsHref} onClick={() => setOpen(false)}>
          Settings
        </Link>
        {mode === "prod" ? (
          <form action={signOut}>
            <button className="user-menu-signout" type="submit">
              Sign out
            </button>
          </form>
        ) : (
          <span className="user-menu-note">Sample account · demo only</span>
        )}
      </div>
    </div>
  );
}
