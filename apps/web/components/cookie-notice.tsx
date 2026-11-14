"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

const STORAGE_KEY = "trendrail-cookie-notice-v1";

export function CookieNotice({ variant = "bar" }: { variant?: "bar" | "brand" }) {
  const pathname = usePathname();
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (localStorage.getItem(STORAGE_KEY) !== "acknowledged") {
      setVisible(true);
    }
  }, []);

  if (!visible) return null;

  function acknowledge() {
    localStorage.setItem(STORAGE_KEY, "acknowledged");
    setVisible(false);
  }

  const isBrand = variant === "brand";
  const className = isBrand
    ? "cookie-brand"
    : `cookie-notice${pathname === "/login" ? " cookie-notice-login" : ""}`;

  return (
    <>
      <link rel="stylesheet" href="/assets/css/cookie.css" />
      <section className={className} aria-label="Cookie notice">
        <div className="cookie-head">
          <span className="cookie-icon" aria-hidden="true">
            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.8"
              aria-hidden="true"
              focusable="false"
            >
              <path d="M20.8 12.6A9 9 0 1 1 11.4 3.2a3.6 3.6 0 0 0 4.5 4.5 3.6 3.6 0 0 0 4.9 4.9z" />
              <circle cx="9" cy="11" r="1" fill="currentColor" stroke="none" />
              <circle cx="8.5" cy="15.5" r="1" fill="currentColor" stroke="none" />
              <circle cx="13.5" cy="16.5" r="0.9" fill="currentColor" stroke="none" />
            </svg>
          </span>
          <div>
            <span className="cookie-eyebrow">Cookie notice</span>
            <h2 className="cookie-title">Essential cookies</h2>
          </div>
        </div>
        <p className="cookie-copy">
          We use essential cookies only for sign-in and security. No analytics or advertising
          cookies.
        </p>
        <div className="cookie-actions">
          <Link className="cookie-more" href="/privacy">
            Details
          </Link>
          <button className="btn btn-primary cookie-accept" type="button" onClick={acknowledge}>
            Accept
          </button>
        </div>
      </section>
    </>
  );
}
