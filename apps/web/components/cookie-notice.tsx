"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

const STORAGE_KEY = "trendrail-cookie-notice-v1";

export function CookieNotice() {
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

  return (
    <>
      <link rel="stylesheet" href="/assets/css/cookie.css" />
      <section className="cookie-notice" aria-label="Cookie notice">
        <div className="cookie-copy">
          <b>คุกกี้ที่จำเป็น</b>
          <p>เว็บไซต์นี้ใช้คุกกี้เฉพาะที่จำเป็นสำหรับการเข้าสู่ระบบและความปลอดภัย ไม่มีคุกกี้ วิเคราะห์หรือโฆษณา</p>
        </div>
        <div className="cookie-actions">
          <Link className="btn btn-ghost" href="/privacy#cookies">
            รายละเอียด
          </Link>
          <button className="btn btn-primary" type="button" onClick={acknowledge}>
            รับทราบ
          </button>
        </div>
      </section>
    </>
  );
}
