import { getDashboard, type Development } from "@/lib/api";

const money = (n?: number | null) => n == null ? "Not reported" : `₹${n.toLocaleString("en-IN")} Cr`;
const label = (s: string) => s.replaceAll("_", " ");

function Metric({ title, value, note }: { title: string; value: string | number; note: string }) {
  return <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
    <p className="text-sm text-slate-400">{title}</p><p className="mt-2 text-3xl font-semibold tracking-tight">{value}</p>
    <p className="mt-2 text-xs text-slate-500">{note}</p>
  </div>;
}

function RecordCard({ item }: { item: Development }) {
  return <article className="rounded-2xl border border-white/10 bg-[#101c2d] p-5">
    <div className="flex flex-wrap items-center justify-between gap-2">
      <span className="rounded-full bg-cyan-300/10 px-3 py-1 text-xs capitalize text-cyan-200">{item.category}</span>
      <span className="rounded-full bg-white/5 px-3 py-1 text-xs capitalize text-slate-300">{label(item.status)}</span>
    </div>
    <h3 className="mt-4 text-lg font-semibold">{item.title}</h3>
    <p className="mt-2 text-sm leading-6 text-slate-400">{item.summary}</p>
    <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
      <div><p className="text-xs text-slate-500">District</p><p className="mt-1">{item.district ?? "Statewide / not specified"}</p></div>
      <div><p className="text-xs text-slate-500">Investment</p><p className="mt-1">{money(item.investment_inr_crore)}</p></div>
      <div><p className="text-xs text-slate-500">Expected jobs</p><p className="mt-1">{item.expected_jobs?.toLocaleString("en-IN") ?? "Not reported"}</p></div>
      <div><p className="text-xs text-slate-500">Jobs created</p><p className="mt-1">{item.jobs_created?.toLocaleString("en-IN") ?? "Not verified"}</p></div>
    </div>
    <p className="mt-4 border-t border-white/10 pt-3 text-[11px] uppercase tracking-wider text-amber-300">Illustrative demo record · Not a verified claim</p>
  </article>;
}

export default async function Home() {
  const data = await getDashboard();
  const items = data.recent_developments as Development[];
  const metrics = data.metrics;
  return <main className="min-h-screen">
    <header className="border-b border-white/10 bg-[#0b1728]/90">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
        <div><p className="text-xs font-semibold tracking-[.24em] text-cyan-300">PUBLIC DEVELOPMENT TRACKER</p><p className="mt-1 text-lg font-bold">AP Development Intelligence</p></div>
        <nav className="hidden gap-6 text-sm text-slate-400 md:flex"><a href="#developments">Developments</a><a href="#districts">Districts</a><a href="#schemes">Schemes</a><a href="#about">About</a></nav>
        <span className="rounded-full border border-emerald-400/30 px-3 py-1 text-xs text-emerald-300">Public beta</span>
      </div>
    </header>

    <section className="mx-auto max-w-7xl px-6 pb-10 pt-16">
      <div className="max-w-3xl">
        <p className="text-sm font-medium text-cyan-300">ANDHRA PRADESH · DEVELOPMENT, INVESTMENT & PUBLIC IMPACT</p>
        <h1 className="mt-5 text-4xl font-bold leading-tight tracking-tight md:text-6xl">Understand what is changing across <span className="text-cyan-300">Andhra Pradesh.</span></h1>
        <p className="mt-5 max-w-2xl text-base leading-7 text-slate-400">Explore investment announcements, project progress, government schemes and district-level developments — with sources and transparent status tracking.</p>
        <div className="mt-7 flex flex-wrap gap-3"><a href="#developments" className="rounded-xl bg-cyan-300 px-5 py-3 text-sm font-semibold text-slate-950">Explore developments</a><a href="#about" className="rounded-xl border border-white/15 px-5 py-3 text-sm text-slate-200">How data is verified</a></div>
      </div>
    </section>

    <section className="mx-auto max-w-7xl px-6">
      <div className="mb-4 rounded-xl border border-amber-300/20 bg-amber-300/[0.07] p-4 text-sm text-amber-100"><strong>Data transparency:</strong> {data.notice} All sample figures below are illustrative and must not be treated as actual government statistics.</div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <Metric title="Tracked records" value={metrics.tracked_records} note="Illustrative sample count" />
        <Metric title="MoUs signed" value={metrics.mou_signed} note="Demo records only" />
        <Metric title="Projects grounded" value={metrics.grounded} note="Demo records only" />
        <Metric title="Operational" value={metrics.operational} note="Demo records only" />
        <Metric title="Verified jobs created" value={metrics.verified_jobs_created} note="No verified jobs in demo" />
      </div>
    </section>

    <section id="developments" className="mx-auto max-w-7xl px-6 py-14">
      <div className="mb-6"><p className="text-sm text-cyan-300">WHAT'S BEING TRACKED</p><h2 className="mt-2 text-2xl font-bold">Development explorer</h2><p className="mt-2 text-sm text-slate-400">Each record should eventually include its source, publication date, district and verification history.</p></div>
      <div className="grid gap-4 lg:grid-cols-3">{items.map(item => <RecordCard key={item.id} item={item} />)}</div>
    </section>

    <section id="districts" className="mx-auto max-w-7xl px-6 pb-12">
      <div className="rounded-3xl border border-white/10 bg-gradient-to-br from-[#10243a] to-[#0d1726] p-8">
        <p className="text-sm text-cyan-300">DISTRICT INTELLIGENCE</p><h2 className="mt-2 text-2xl font-bold">Explore all 28 districts</h2>
        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">The next milestone adds district boundaries, project pins, investment filters and district profiles. We will use official boundary data rather than guessed map coordinates.</p>
        <div className="mt-6 grid grid-cols-2 gap-2 text-sm sm:grid-cols-4 lg:grid-cols-6">{["Alluri Sitharama Raju","Anakapalli","Anantapur","Annamayya","Bapatla","Chittoor","Dr. B.R. Ambedkar Konaseema","East Godavari","Eluru","Guntur","Kakinada","Krishna","Kurnool","Markapuram","Nandyal","NTR","Palnadu","Parvathipuram Manyam","Polavaram","Prakasam","Sri Potti Sriramulu Nellore","Sri Sathya Sai","Srikakulam","Tirupati","Visakhapatnam","Vizianagaram","West Godavari","YSR Kadapa"].map(d => <span key={d} className="rounded-lg border border-white/10 bg-black/10 px-3 py-2 text-slate-300">{d}</span>)}</div>
      </div>
    </section>

    <section id="schemes" className="mx-auto max-w-7xl px-6 pb-14">
      <div className="rounded-3xl border border-white/10 p-8"><p className="text-sm text-cyan-300">GOVERNMENT SCHEMES</p><h2 className="mt-2 text-2xl font-bold">Make public benefits easier to understand</h2><p className="mt-3 max-w-2xl text-sm leading-6 text-slate-400">Upcoming: searchable scheme catalogue with eligibility, benefit amount, application link, department, district coverage and official source.</p></div>
    </section>

    <footer id="about" className="border-t border-white/10 px-6 py-8 text-center text-xs leading-6 text-slate-500">Independent public information project · Not an official Government of Andhra Pradesh website. Data must be checked against linked primary sources before publication.</footer>
  </main>;
}
