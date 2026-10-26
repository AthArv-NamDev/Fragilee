'use client';
import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { supabaseBrowser } from '@/lib/supabase/client';
import { loadBoards, signedUrls, copyText, missingFor } from '@/lib/data';
import { post } from '@/lib/api';
import ExportPanel from '@/components/ExportPanel';
import { getTimes, setTime } from '@/lib/times';
import { weekend, pretty } from '@/lib/dates';

const TABS = [['post', 'Ready to post'], ['drafts', 'Drafts'], ['posted', 'Posted']];

export default function Queue() {
  const s = useMemo(() => supabaseBrowser(), []);
  const [tab, setTab] = useState('post');
  const [pins, setPins] = useState([]);
  const [boards, setBoards] = useState([]);
  const [urls, setUrls] = useState({});
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(true);
  const [writing, setWriting] = useState(false);
  const [times, setTimes] = useState({});

  async function load() {
    const [p, b] = await Promise.all([s.from('pins').select('*').order('created_at', { ascending: false }).limit(200), loadBoards(s)]);
    if (p.error) setMsg(p.error.message);
    setPins(p.data || []);
    setBoards(b);
    setUrls(await signedUrls(s, (p.data || []).map((x) => x.image_path)));
    setLoading(false);
  }
  useEffect(() => { setTimes(getTimes()); load(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const shown = useMemo(() => {
    const by = (st) => pins.filter((p) => st.includes(p.status));
    if (tab === 'post') return by(['optimized', 'scheduled']).sort((a, b) => ((a.scheduled_for || '9999') + (times[a.id] || '')).localeCompare((b.scheduled_for || '9999') + (times[b.id] || '')));
    if (tab === 'drafts') return by(['idea', 'image_ready']);
    return by(['posted']).sort((a, b) => (b.posted_at || '').localeCompare(a.posted_at || '')).slice(0, 30);
  }, [pins, tab, times]);

  const where = (p) => {
    const b = boards.find((x) => x.id === p.board_id);
    const sec = b?.sections.find((x) => x.id === p.section_id);
    return b ? (sec ? `${b.name}, ${sec.name}` : b.name) : 'No board yet';
  };
  function changeTime(id, t) { setTime(id, t); setTimes(getTimes()); }
  async function patch(id, fields) {
    const { error } = await s.from('pins').update(fields).eq('id', id);
    if (error) { setMsg(error.message); return false; }
    setPins((prev) => prev.map((p) => (p.id === id ? { ...p, ...fields } : p)));
    return true;
  }
  async function fillWeekend() {
    const { sat, sun } = weekend();
    const count = { [sat]: 0, [sun]: 0 };
    pins.forEach((p) => { if (p.status === 'scheduled' && count[p.scheduled_for] !== undefined) count[p.scheduled_for]++; });
    const open = pins.filter((p) => p.status === 'optimized' && !p.scheduled_for);
    if (!open.length) return setMsg('No unscheduled ready pins to place.');
    let n = 0;
    for (const p of open) {
      const day = [sat, sun].find((d) => count[d] < 5);
      if (!day) break;
      if (await patch(p.id, { scheduled_for: day, status: 'scheduled' })) { count[day]++; n++; }
    }
    setMsg(n ? `Placed ${n} pin${n > 1 ? 's' : ''} on this weekend.` : 'This weekend is already full.');
  }
  async function writeAll() {
    const need = pins.filter((p) => ['idea', 'image_ready'].includes(p.status) && (!p.title || !p.description || !p.board_id)).slice(0, 12);
    if (!need.length) return setMsg('No drafts need words.');
    setWriting(true); setMsg('');
    try {
      const ideaIds = need.map((p) => p.idea_id).filter(Boolean);
      const { data: ideas } = ideaIds.length ? await s.from('ideas').select('id,title,angle').in('id', ideaIds) : { data: [] };
      const idea = Object.fromEntries((ideas || []).map((i) => [i.id, [i.title, i.angle].filter(Boolean).join('. ')]));
      const items = need.map((p) => ({ id: p.id, concept: p.concept || idea[p.idea_id] || p.title || '' }));
      const d = await post('/api/ai/seo-batch', { items, boards });
      let n = 0;
      for (const r of d.results) {
        const p = pins.find((x) => x.id === r.id);
        if (!p) continue;
        const next = { title: p.title || r.title, description: p.description || r.description, board_id: p.board_id || r.board_id, section_id: p.section_id || r.section_id };
        if (p.image_path && next.title && next.description && next.board_id) next.status = p.scheduled_for ? 'scheduled' : 'optimized';
        if (await patch(p.id, next)) n++;
      }
      setMsg(`Wrote words for ${n} pin${n === 1 ? '' : 's'}. Ones with an image and a board are now ready to post.${d.provider === 'groq' ? ' (Written by the backup AI.)' : ''}`);
    } catch (e) { setMsg(e.message); }
    setWriting(false);
  }
  async function copy(text, what) { setMsg((await copyText(text || '')) ? `${what} copied.` : 'Could not copy. Select the text and copy it by hand.'); }
  async function download(p) {
    const ext = p.image_path.split('.').pop();
    const name = (p.title || 'pin').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40) || 'pin';
    const { data, error } = await s.storage.from('pins').createSignedUrl(p.image_path, 300, { download: `${name}.${ext}` });
    if (error) return setMsg(error.message);
    location.href = data.signedUrl;
  }
  async function remove(p) {
    if (!confirm('Delete this pin? This cannot be undone.')) return;
    const { error } = await s.from('pins').delete().eq('id', p.id);
    if (error) return setMsg(error.message);
    if (p.image_path) await s.storage.from('pins').remove([p.image_path]);
    setPins((prev) => prev.filter((x) => x.id !== p.id));
  }

  return (
    <>
      <h1>Queue</h1>
      <div className="chips" role="tablist">
        {TABS.map(([k, label]) => <button key={k} role="tab" className="chip" aria-pressed={tab === k} onClick={() => setTab(k)}>{label}</button>)}
      </div>
      {tab === 'post' && <div className="row"><Link className="primary" href="/post">Start posting</Link><button className="line" onClick={fillWeekend}>Fill this weekend</button></div>}
      {tab === 'post' && <ExportPanel pins={pins} boards={boards} patch={patch} setMsg={setMsg} times={times} changeTime={changeTime} />}
      {tab === 'drafts' && shown.length > 0 && (
        <div className="row">
          <button className="primary" onClick={writeAll} disabled={writing}>{writing ? 'Writing…' : 'Write words for all drafts'}</button>
          <span className="tag">One Gemini request for up to 12 pins.</span>
        </div>
      )}
      {msg && <p className="note" role="status" key={msg}>{msg}</p>}
      {loading && <p className="muted">Loading…</p>}
      {!loading && shown.length === 0 && (
        <p className="muted">{tab === 'post' ? 'Nothing ready yet. Finish a pin in the pin maker.' : tab === 'drafts' ? 'No drafts.' : 'Nothing posted yet.'}</p>
      )}
      <ul className="list">
        {shown.map((p) => (
          <li className="pin" key={p.id}>
            {urls[p.image_path] ? <img className="thumb" src={urls[p.image_path]} alt="" /> : <div className="thumb" />}
            <div className="stack">
              <h3>{p.title || 'Untitled draft'}</h3>
              <p className="tag">{where(p)}</p>
              {tab === 'drafts' && <p className="tag err">Missing: {missingFor(p).join(', ') || 'nothing'}</p>}
              {tab === 'post' && (
                <label className="tag">Post on{' '}
                  <input type="date" value={p.scheduled_for || ''} onChange={(e) => patch(p.id, { scheduled_for: e.target.value || null, status: e.target.value ? 'scheduled' : 'optimized' })} />
                </label>
              )}
              {tab === 'post' && (
                <label className="tag">at{' '}
                  <input type="time" value={times[p.id] || ''} onChange={(e) => changeTime(p.id, e.target.value)} />
                </label>
              )}
              {tab === 'posted' && p.posted_at && <p className="tag ok">Posted {new Date(p.posted_at).toLocaleDateString('en-IN')}</p>}
              {tab === 'post' && (
                <div className="row">
                  <button className="line" onClick={() => copy(p.title, 'Title')}>Copy title</button>
                  <button className="line" onClick={() => copy(p.description, 'Description')}>Copy description</button>
                  <button className="line" onClick={() => download(p)}>Save image</button>
                  <a className="line" href="https://www.pinterest.com/pin-creation-tool/" target="_blank" rel="noopener noreferrer">Open Pinterest</a>
                  <button className="primary" onClick={() => patch(p.id, { status: 'posted', posted_at: new Date().toISOString() })}>Mark posted</button>
                </div>
              )}
              {tab !== 'posted' && (
                <div className="row"><Link className="quiet" href={`/maker?pin=${p.id}`}>{tab === 'drafts' ? 'Continue' : 'Edit'}</Link><button className="quiet" onClick={() => remove(p)}>Delete</button></div>
              )}
              {tab === 'post' && p.destination_url && <p className="tag">Link: {p.destination_url}</p>}
            </div>
          </li>
        ))}
      </ul>
    </>
  );
}
