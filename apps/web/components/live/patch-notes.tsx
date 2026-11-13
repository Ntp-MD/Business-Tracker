"use client";

import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export function PatchNotes() {
  const [open, setOpen] = useState(false);
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") setOpen(false);
    }
    document.addEventListener("keydown", onKey);
    closeRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [open]);

  return (
    <>
      <button
        className="btn btn-ghost ver-btn"
        type="button"
        aria-haspopup="dialog"
        onClick={() => setOpen(true)}
      >
        Patch notes
      </button>
      {open &&
        createPortal(
          // biome-ignore lint/a11y/noStaticElementInteractions: backdrop click-to-close; the dialog has its own close button
          <div className="loading-overlay" role="presentation" onClick={() => setOpen(false)}>
            {/* biome-ignore lint/a11y/useKeyWithClickEvents: only stops backdrop click bubbling; not an action */}
            <div
              className="loading-card notes-card"
              role="dialog"
              aria-modal="true"
              aria-labelledby="notesTitle"
              onClick={(event) => event.stopPropagation()}
            >
              <div className="notes-head">
                <div>
                  <div className="loading-title" id="notesTitle">
                    Patch notes
                  </div>
                  <div className="loading-sub">TrendRail 0.3 · 13 พ.ย. 2026</div>
                </div>
                <button
                  className="btn btn-ghost notes-close"
                  type="button"
                  aria-label="ปิด patch notes"
                  ref={closeRef}
                  onClick={() => setOpen(false)}
                >
                  ✕
                </button>
              </div>
              <ol className="timeline">
                <li className="tl-item current">
                  <div className="tl-top">
                    <b>0.3</b>
                    <span className="tl-date">13 พ.ย. 2026</span>
                    <span className="pill pill-green">current</span>
                  </div>
                  <p className="tl-note">Mockup เต็มรูปแบบ + login และ privacy พร้อมพรีเซนต์</p>
                  <ul className="tl-list">
                    <li>Mockup แยกจาก prod/live ชัดเจน พร้อมข้อมูลตัวอย่างครบ 14 เมนู</li>
                    <li>หน้า login ใหม่, magic link + password fallback และ URL สะอาด</li>
                    <li>ประกาศ PDPA ที่ /privacy และ cookie notice แบบจำเป็นเท่านั้น</li>
                    <li>Live read-only ด้วย anon key + views, health alert และ E2E 3 variants</li>
                    <li>ปุ่มดูเดโมเปิด mockup โดยไม่แตะข้อมูล production</li>
                  </ul>
                </li>
                <li className="tl-item">
                  <div className="tl-top">
                    <b>0.2</b>
                    <span className="tl-date">11 พ.ย. 2026</span>
                  </div>
                  <p className="tl-note">ย้ายไป Next.js + Supabase + Vercel</p>
                  <ul className="tl-list">
                    <li>หน้า live ทั้งหมดเป็น React และอ่านข้อมูลจาก Supabase</li>
                    <li>CRUD, bulk archive/delete/move, CSV และ JSON import/export</li>
                    <li>Search Now ผ่าน job queue + worker บนเครื่อง owner</li>
                    <li>แบรนด์ใหม่ TrendRail พร้อมโลโก้และ favicon</li>
                  </ul>
                </li>
                <li className="tl-item">
                  <div className="tl-top">
                    <b>0.1</b>
                    <span className="tl-date">10 พ.ย. 2026</span>
                  </div>
                  <p className="tl-note">Dashboard ใช้งานจริงบนเครื่อง</p>
                  <ul className="tl-list">
                    <li>ค้นเทรนด์ 5 ช่องทาง: YouTube, Google News, TikTok, FB Ads, TikTok Ads</li>
                    <li>โปรไฟล์คำค้น, ช่วงเวลา, archive/trash, export/import</li>
                  </ul>
                </li>
              </ol>
            </div>
          </div>,
          document.body,
        )}
    </>
  );
}
