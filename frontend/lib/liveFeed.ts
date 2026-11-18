export type LiveItem={id:string;title:string;summary:string;category:string;district:string|null;sector:string|null;stage:string;verification:string;source_name:string|null;source_url:string|null;source_published_on?:string|null;source_collected_at?:string|null;investment_inr_crore:number|null;expected_jobs:number|null;jobs_created:number|null};
export type LiveFeed={verified:{count:number;items:LiveItem[];notice:string};unverified:{count:number;items:LiveItem[];notice:string}};
export const safeExternal=(url:string|null)=>url&&/^https?:\/\//i.test(url)?url:null;
export const districtMatch=(a:string|null,b:string)=>Boolean(a&&a.trim().toLowerCase()===b.trim().toLowerCase());
