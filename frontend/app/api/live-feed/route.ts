import {NextResponse} from 'next/server';
export const dynamic='force-dynamic';
export async function GET(){
 const base=process.env.APDI_API_BASE_URL||process.env.API_BASE_URL||process.env.NEXT_PUBLIC_API_BASE_URL||'http://localhost:8000';
 try {const response=await fetch(`${base}/api/v1/public/intelligence?limit=100`,{cache:'no-store',signal:AbortSignal.timeout(6000)});
 if(!response.ok)throw new Error(`HTTP ${response.status}`);
 return NextResponse.json(await response.json(),{headers:{'Cache-Control':'no-store'}});
 }catch{return NextResponse.json({error:'Live intelligence is unavailable; no demo fallback has been substituted.'},{status:503,headers:{'Cache-Control':'no-store'}})}
}
