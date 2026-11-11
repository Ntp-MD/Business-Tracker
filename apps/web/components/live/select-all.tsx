"use client";

import { useEffect, useRef } from "react";

export function SelectAll({ label = "Select all rows" }: { label?: string }) {
  const ref = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const box = ref.current;
    const form = box?.closest("form");
    if (!box || !form) return;

    const boxes = () => Array.from(form.querySelectorAll<HTMLInputElement>('input[name="ids"]'));
    const sync = () => {
      const all = boxes();
      const checked = all.filter((item) => item.checked).length;
      box.checked = all.length > 0 && checked === all.length;
      box.indeterminate = checked > 0 && checked < all.length;
    };

    form.addEventListener("change", sync);
    sync();
    return () => form.removeEventListener("change", sync);
  }, []);

  return (
    <input
      ref={ref}
      type="checkbox"
      aria-label={label}
      onChange={(event) => {
        const form = event.currentTarget.closest("form");
        if (!form) return;
        for (const item of form.querySelectorAll<HTMLInputElement>('input[name="ids"]')) {
          item.checked = event.currentTarget.checked;
        }
        event.currentTarget.indeterminate = false;
      }}
    />
  );
}
