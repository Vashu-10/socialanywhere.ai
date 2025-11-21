import { useEffect, useMemo } from "react";
import { Link } from "react-router-dom";
import { useCampaignStore } from "../store/campaignStore.js";

function MyCampaigns() {
  const campaigns = useCampaignStore((s) => s.campaigns);
  const loadCampaignsFromDB = useCampaignStore((s) => s.loadCampaignsFromDB);

  useEffect(() => { loadCampaignsFromDB(); }, [loadCampaignsFromDB]);

  const rows = useMemo(() => {
    const sumReach = (m) => {
      if (!m) return 0;
      if (typeof m.reach === 'number') return m.reach;
      if (typeof m.impressions === 'number') return m.impressions;
      return 0;
    };
    const sumEngagement = (m) => {
      if (!m) return 0;
      if (typeof m.engaged_users === 'number') return m.engaged_users;
      const r = m.reactions || {};
      const likes = Number(r.like || r.likes || 0);
      const comments = Number(m.comments || 0);
      const shares = Number(m.shares || 0);
      const saves = Number(m.saves || 0);
      return likes + comments + shares + saves;
    };

    const map = new Map();
    for (const c of campaigns) {
      const key = (c.campaignName && c.campaignName.trim()) || c.batchId || c.id;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(c);
    }
    return Array.from(map.entries()).map(([key, items]) => {
      const total = items.length;
      const scheduled = items.filter(i => i.status === 'Scheduled').length;
      const posted = items.filter(i => i.status === 'Posted').length;
      const name = items[0]?.campaignName || items[0]?.productDescription || 'Untitled Campaign';
      const allPlatforms = Array.from(new Set(items.flatMap(i => i.platforms || (i.platform ? [i.platform] : [])))).filter(Boolean);
      const next = items.map(i => i.scheduledAt).filter(Boolean).map(d=>new Date(d)).filter(d=>!isNaN(d)).sort((a,b)=>a-b)[0] || null;
      const reach = items.reduce((acc, it) => acc + sumReach(it.engagementMetrics), 0);
      const engagement = items.reduce((acc, it) => acc + sumEngagement(it.engagementMetrics), 0);
      return {
        id: String(key),
        name,
        status: posted>0 ? 'Active' : (scheduled>0 ? 'Scheduled' : 'Draft'),
        platforms: allPlatforms,
        posts: total,
        reach: reach || '-',
        engagement: engagement || '-',
        scheduledAt: next,
        createdAt: items[0]?.createdAt || Date.now(),
      };
    }).sort((a,b)=> (b.createdAt||0)-(a.createdAt||0));
  }, [campaigns]);

  const stats = useMemo(()=>({
    total: rows.length,
    active: rows.filter(r=>r.status==='Active').length,
    scheduled: rows.filter(r=>r.status==='Scheduled').length,
    drafts: rows.filter(r=>r.status==='Draft').length,
  }), [rows]);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">My Campaigns</h1>
          <p className="text-sm text-gray-500">Manage and track your social media campaigns</p>
        </div>
        <Link to="/create" className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-600 text-white hover:bg-purple-700">New Campaign</Link>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {[{label:'Total Campaigns', value:stats.total}, {label:'Active', value:stats.active}, {label:'Scheduled', value:stats.scheduled}, {label:'Drafts', value:stats.drafts}].map((s,i)=> (
          <div key={i} className="rounded-2xl border border-gray-200 bg-white p-6">
            <div className="text-sm text-gray-500 mb-2">{s.label}</div>
            <div className="text-3xl font-semibold text-gray-900">{s.value}</div>
          </div>
        ))}
      </div>

      <div className="rounded-2xl border border-gray-200 bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead className="bg-gray-50 text-gray-600">
              <tr>
                <th className="text-left px-6 py-3 font-medium">Campaign Name</th>
                <th className="text-left px-6 py-3 font-medium">Status</th>
                <th className="text-left px-6 py-3 font-medium">Platforms</th>
                <th className="text-left px-6 py-3 font-medium">Posts</th>
                <th className="text-left px-6 py-3 font-medium">Reach</th>
                <th className="text-left px-6 py-3 font-medium">Engagement</th>
                <th className="text-left px-6 py-3 font-medium">Scheduled</th>
                <th className="px-6 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {rows.map(row => (
                <tr key={row.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900">{row.name}</div>
                    <div className="text-xs text-gray-500">Created {new Date(row.createdAt).toISOString().slice(0,10)}</div>
                  </td>
                  <td className="px-6 py-4">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium ${row.status==='Active' ? 'bg-green-50 text-green-700' : (row.status==='Scheduled' ? 'bg-blue-50 text-blue-700' : 'bg-gray-100 text-gray-700')}`}>{row.status}</span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      {row.platforms.slice(0,4).map(p => (
                        <img key={p} src={`/icons/${p==='twitter'?'x':p}.png`} alt={p} className="w-5 h-5" />
                      ))}
                    </div>
                  </td>
                  <td className="px-6 py-4">{row.posts}</td>
                  <td className="px-6 py-4">{row.reach}</td>
                  <td className="px-6 py-4">{row.engagement}</td>
                  <td className="px-6 py-4">{row.scheduledAt ? new Date(row.scheduledAt).toISOString().slice(0,10) : '-'}</td>
                  <td className="px-6 py-4 text-right">
                    <button className="p-2 rounded hover:bg-gray-100" title="More">
                      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/><circle cx="5" cy="12" r="1"/></svg>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

export default MyCampaigns;
