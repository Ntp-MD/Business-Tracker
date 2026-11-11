import type { Item } from "@/lib/types";

/** Fixtures for the `/` mock route. No network, no Supabase. */
const BASE: [string, string, string, string, number, number][] = [
  ["Digital Marketing", "facebook", "How we get local clients in 30 days", "ITOPPLUS Case", 891, 12000],
  ["Digital Marketing", "tiktok", "Facebook Ads vs TikTok Ads: where to start", "ads.withbeam", 642, 8400],
  ["Digital Marketing", "facebook", "Content strategy ที่ยิงแล้วได้ลูกค้าจริง", "ITOPPLUS", 534, 6100],
  ["SEO", "youtube", "SEO สำหรับธุรกิจไทย 2026", "Nack Siwakorn", 478, 5200],
  ["SEO", "facebook", "Local SEO ทำอย่างไรให้ร้านถูกเจอ", "Local Heroes", 412, 4300],
  ["เว็บขายของ", "tiktok", "ร้านค้าออนไลน์ควรมีเว็บของตัวเองไหม", "Commerce TH", 388, 3900],
  ["เว็บขายของ", "instagram", "LINE OA กับเว็บไซต์ เลือกอะไรก่อน", "ITOPPLUS", 301, 3100],
  ["ระบบจอง", "facebook", "ระบบจองคิวที่ลด no-show ได้จริง", "Booking TH", 276, 2600],
  ["ระบบจอง", "youtube", "ทำระบบจองเองหรือใช้ SaaS ดี", "Dev Thai", 254, 2300],
  ["ธีมเว็บ", "tiktok", "ธีมเว็บแบบไหนขายของได้", "Web Theme Lab", 198, 1800],
  ["ธีมเว็บ", "facebook", "เลือกธีมเว็บให้ตรงกลุ่มลูกค้า", "Design TH", 174, 1500],
  ["ค่า LINE OA", "youtube", "ค่า LINE OA คุ้มไหมสำหรับ SME", "LINE Business TH", 152, 1300],
];

export const MOCK_ITEMS: Item[] = Array.from({ length: 67 }, (_, index) => {
  const [keyword, source, title, author, score, views] = BASE[index % BASE.length];
  const cycle = Math.floor(index / BASE.length);
  return {
    id: `mock-${index + 1}`,
    keyword,
    source,
    url: `https://example.com/mock/${index + 1}`,
    canonical_url: `https://example.com/mock/${index + 1}`,
    title: cycle ? `${title} · part ${cycle + 1}` : title,
    body: "",
    author,
    channel_url: "",
    score: score + cycle * 7,
    metric: "views",
    views: views + cycle * 50,
    published: "2026-11-01",
    created_at: "2026-11-01T00:00:00Z",
    asset: null,
    created: "",
    archived_at: "",
    deleted_at: "",
  };
});

export const MOCK_PROFILES = [
  { name: "Profile 1 — ITOPPLUS", keywords: ["Digital Marketing", "SEO", "เว็บขายของ"], sources: ["facebook", "tiktok"] },
  { name: "Local business", keywords: ["ระบบจอง", "ธีมเว็บ"], sources: ["youtube", "facebook"] },
];

export const SOURCE_LABELS: Record<string, string> = {
  youtube: "YouTube",
  gnews: "Google News",
  tiktok: "TikTok",
  facebook: "Facebook",
  fbads: "FB Ads",
  ttads: "TikTok Ads",
  instagram: "Instagram",
  line: "LINE OA",
};

export function mockSourceLabel(source: string): string {
  return SOURCE_LABELS[source] ?? source;
}

export function mockBand(score: number): string {
  if (score >= 500) return "Hot";
  if (score >= 300) return "Rising";
  return "Steady";
}

export function mockTerms(): [string, number][] {
  const counts = new Map<string, number>();
  for (const item of MOCK_ITEMS) {
    for (const word of item.title.toLowerCase().split(/\s+/)) {
      const clean = word.replace(/[.,:;()"'[\]]/g, "");
      if (clean.length >= 4) counts.set(clean, (counts.get(clean) ?? 0) + 1);
    }
  }
  return [...counts.entries()].sort((a, b) => b[1] - a[1]).slice(0, 12);
}
