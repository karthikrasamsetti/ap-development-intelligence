import Link from "next/link";

type Item = { snapshot_id: number; title: string; source_name: string; source_url: string | null; fetched_at: string | null; verification: string };
type Feed = { notice: string; items: Item[] };
export const dynamic = "force-dynamic";
async function getFeed(): Promise<{feed: Feed | null; error: boolean}> {
  const base = process.env.API_BASE_URL || process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";
  try {
    const res = await fetch(`${base}/api/v1/public/source-updates`, {cache: "no-store", signal: AbortSignal.timeout(5000)});
    if (!res.ok) throw new Error("Unavailable");
    return {feed: await res.json() as Feed, error: false};
  } catch { return {feed: null, error: true}; }
}
export default async function UpdatesPage() {
  const {feed, error} = await getFeed();
  return <main style={{minHeight:"100vh",background:"#f5f9fb",color:"#183247",fontFamily:"system-ui, sans-serif"}}>
    <div style={{maxWidth:1120,margin:"auto",padding:"32px 20px 80px"}}>
      <nav style={{display:"flex",justifyContent:"space-between",alignItems:"center",gap:16,marginBottom:52}}><Link href="/" style={{color:"#087e72",fontWeight:800,textDecoration:"none"}}>AP. Development Intelligence</Link><Link href="/" style={{color:"#31566b"}}>← Dashboard</Link></nav>
      <p style={{color:"#008c7b",fontSize:12,fontWeight:800,letterSpacing:2}}>SOURCE INTELLIGENCE</p>
      <h1 style={{fontSize:"clamp(32px,5vw,58px)",letterSpacing:"-0.05em",margin:"12px 0"}}>Latest collected sources</h1>
      <p style={{maxWidth:760,lineHeight:1.7,color:"#526a7c"}}>A transparent view of what APDI has collected. These are observations of source pages, not verified development announcements. Source collection timestamps are not news publication dates.</p>
      <div style={{background:"#e6f5ef",border:"1px solid #b9e2d2",padding:18,borderRadius:14,margin:"30px 0",lineHeight:1.6}}>{feed?.notice || "Source feed unavailable. Check that the FastAPI backend is running and the v14 backend patch is installed."}</div>
      {error ? <p role="alert">Unable to load source observations from the API.</p> : feed?.items.length === 0 ? <p>No source observations collected yet.</p> :
      <div style={{display:"grid",gridTemplateColumns:"repeat(auto-fit,minmax(min(100%,320px),1fr))",gap:18}}>{feed?.items.map(item => <article key={item.snapshot_id} style={{background:"white",border:"1px solid #dce8ed",borderRadius:16,padding:24,boxShadow:"0 6px 20px #14344808"}}>
        <div style={{fontSize:12,color:"#008c7b",fontWeight:700}}>SOURCE OBSERVATION · #{item.snapshot_id}</div>
        <h2 style={{fontSize:20,lineHeight:1.35,margin:"12px 0"}}>{item.title}</h2>
        <p style={{fontSize:14,color:"#617689"}}>Publisher / source: {item.source_name}</p>
        <p style={{fontSize:13,color:"#617689"}}>Collected: {item.fetched_at ? new Date(item.fetched_at).toLocaleString("en-IN",{dateStyle:"medium",timeStyle:"short",timeZone:"Asia/Kolkata"}) + " IST" : "Not recorded"}</p>
        <p style={{fontSize:12,color:"#92641a",fontWeight:700}}>Not yet verified as a development</p>
        {item.source_url && <a href={item.source_url} target="_blank" rel="noopener noreferrer" style={{color:"#008c7b",fontWeight:700}}>Open original source ↗</a>}
      </article>)}</div>}
    </div>
  </main>;
}
