export type Development = {
  id: string; title: string; category: string; district: string | null;
  sector?: string | null; status: string; investment_inr_crore?: number | null;
  expected_jobs?: number | null; jobs_created?: number | null;
  summary: string; is_demo?: boolean;
};

const demo: Development[] = [
  { id: "demo-001", title: "Illustrative renewable energy project", category: "investment", district: "Anantapur", sector: "Renewable energy", status: "mou_signed", investment_inr_crore: 1200, expected_jobs: 850, summary: "Sample record only. Replace with verified source data.", is_demo: true },
  { id: "demo-002", title: "Illustrative port connectivity upgrade", category: "infrastructure", district: "Kakinada", sector: "Transport", status: "grounded", investment_inr_crore: 450, expected_jobs: 200, summary: "Sample record only. Replace with verified source data.", is_demo: true },
  { id: "demo-003", title: "Illustrative farmer support scheme", category: "scheme", district: null, sector: "Agriculture", status: "approved", summary: "Sample statewide scheme entry.", is_demo: true }
];

export async function getDashboard() {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
  try {
    const response = await fetch(`${base}/api/v1/dashboard`, { cache: "no-store", signal: AbortSignal.timeout(1800) });
    if (!response.ok) throw new Error("API unavailable");
    return await response.json();
  } catch {
    return {
      data_mode: "demo",
      notice: "API unavailable. Showing illustrative sample data, not live AP statistics.",
      metrics: { tracked_records: demo.length, mou_signed: 1, grounded: 1, operational: 0, verified_jobs_created: 0 },
      recent_developments: demo
    };
  }
}
