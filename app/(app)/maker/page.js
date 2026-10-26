'use client';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { supabaseBrowser } from '@/lib/supabase/client';
import { loadBoards, signedUrls } from '@/lib/data';
import { post } from '@/lib/api';
import { getTimes, setTime } from '@/lib/times';
import { resizeToJpegBase64, resizeToBlob } from '@/lib/image';

const EMPTY = { concept: '', imagePrompt: '', imagePath: '', title: '', description: '', boardId: '', sectionId: '', dest: '', date: '', time: '' };

export default function Maker() {
  const s = useMemo(() => supabaseBrowser(), []);
  const [boards, setBoards] = useState([]);
  const [f, setF] = useState(EMPTY);
  const [ref, setRef] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [ids, setIds] = useState({ idea: null, pin: null });
  const [busy, setBusy] = useState('');
  const [msg, setMsg] = useState('');
  const [saved, setSaved] = useState('');
  const set = (k, v) => setF((p) => ({ ...p, [k]: v }));
  const board = boards.find((b) => b.id === f.boardId);
  const missing = [!f.imagePath && 'image', !f.title.trim() && 'title', !f.description.trim() && 'description', !f.boardId && 'board'].filter(Boolean);

  useEffect(() => {
    (async () => {
      const q = new URLSearchParams(location.search);
      setBoards(await loadBoards(s));
      if (q.get('pin')) {
        const { data } = await s.from('pins').select('*').eq('id', q.get('pin')).single();
        if (data) {
          setIds({ idea: data.idea_id, pin: data.id });
          setF({ ...EMPTY, concept: data.concept || '', imagePath: data.image_path || '', title: data.title || '', description: data.description || '', boardId: data.board_id || '', sectionId: data.section_id || '', dest: data.destination_url || '', date: data.scheduled_for || '', time: getTimes()[data.id] || '' });
        }
      } else if (q.get('idea')) {
        const { data } = await s.from('ideas').select('*').eq('id', q.get('idea')).single();
        if (data) {
          setIds({ idea: data.id, pin: null });
          setF({ ...EMPTY, concept: [data.title, data.angle].filter(Boolean).join('. '), imagePrompt: data.visual_prompt || '', boardId: data.board_id || '', date: data.target_date || '' });
        }
      }
    })();
  }, [s]);

  useEffect(() => {
    if (!f.imagePath) return setImageUrl('');
    signedUrls(s, [f.imagePath]).then((m) => setImageUrl(m[f.imagePath] || ''));
  }, [f.imagePath, s]);

  async function genImage() {
    if (!f.imagePrompt.trim() && !ref) return setMsg('Describe the image or add a reference first.');
    setBusy('image'); setMsg('');
    try {
      const reference = ref ? { data: await resizeToJpegBase64(ref, 1024), mime: 'image/jpeg' } : null;
      const d = await post('/api/ai/image', { prompt: f.imagePrompt, reference });
      set('imagePath', d.path);
    } catch (e) { setMsg(e.message); }
    setBusy('');
  }
  async function upload(file) {
    if (!file) return;
    setBusy('upload'); setMsg('');
    try {
      const { data: { user } } = await s.auth.getUser();
      const blob = await resizeToBlob(file, 2000);
      const path = `${user.id}/${crypto.randomUUID()}.jpg`;
      const { error } = await s.storage.from('pins').upload(path, blob, { contentType: 'image/jpeg' });
      if (error) throw error;
      set('imagePath', path);
    } catch (e) { setMsg(e.message || 'Upload failed.'); }
    setBusy('');
  }
  async function writeSeo() {
    const concept = f.concept.trim() || f.title.trim();
    if (!concept) return setMsg('Add a short concept first.');
    setBusy('seo'); setMsg('');
    try {
      const d = await post('/api/ai/seo', { concept, boards });
      setF((p) => ({ ...p, title: d.title, description: d.description, boardId: d.board_id || p.boardId, sectionId: d.section_id || '' }));
      if (d.keywords?.length) setMsg(`Search phrases used: ${d.keywords.join(', ')}`);
      if (d.provider === 'groq') setMsg('Written by the backup AI because Gemini was busy or out of requests.');
    } catch (e) { setMsg(e.message); }
    setBusy('');
  }
  async function save() {
    if (f.dest && !/^https?:\/\//i.test(f.dest)) return setMsg('The destination link must start with https://');
    const complete = f.imagePath && f.title.trim() && f.description.trim() && f.boardId;
    const status = complete ? (f.date ? 'scheduled' : 'optimized') : f.imagePath ? 'image_ready' : 'idea';
    const row = {
      concept: f.concept.trim() || null, title: f.title.trim() || null, description: f.description.trim() || null, board_id: f.boardId || null,
      section_id: f.sectionId || null, image_path: f.imagePath || null, destination_url: f.dest || null,
      scheduled_for: f.date || null, idea_id: ids.idea, status,
    };
    setBusy('save'); setMsg('');
    const { data: res, error } = await (ids.pin
      ? s.from('pins').update(row).eq('id', ids.pin).select('id').single()
      : s.from('pins').insert(row).select('id').single());
    setBusy('');
    if (error) return setMsg(error.message);
    setTime(res.id, f.time);
    setSaved(status);
  }
  function reset() { setF(EMPTY); setRef(null); setIds({ idea: null, pin: null }); setSaved(''); setMsg(''); history.replaceState(null, '', '/maker'); }

  if (saved) {
    return (
      <>
        <h1>Pin saved</h1>
        <p>{saved === 'idea' || saved === 'image_ready' ? 'It is in your drafts. Finish it any time from the queue.' : saved === 'scheduled' ? 'It is scheduled and waiting in your queue.' : 'It is ready to post. Place it on a day from the queue.'}</p>
        <div className="row sec"><Link className="primary" href="/queue">Open queue</Link><button className="line" onClick={reset}>Make another</button></div>
      </>
    );
  }

  return (
    <>
      <h1>Pin maker</h1>
      <p className="muted">Concept, image, then words. Save a draft at any point.</p>

      <div className="field"><label htmlFor="concept">Concept</label>
        <textarea id="concept" value={f.concept} onChange={(e) => set('concept', e.target.value)} placeholder="One or two sentences on what this pin shows" /></div>

      <section className="sec">
        <h2>Image</h2>
        {imageUrl ? <img className="preview" src={imageUrl} alt="Pin preview" /> : <p className="muted">No image yet.</p>}
        <div className="field"><label htmlFor="ip">Image prompt</label>
          <textarea id="ip" value={f.imagePrompt} onChange={(e) => set('imagePrompt', e.target.value)} placeholder="Outfit or scene, setting, light, colours" /></div>
        <div className="field"><label htmlFor="ref">Reference to take inspiration from (optional)</label>
          <input id="ref" type="file" accept="image/*" onChange={(e) => setRef(e.target.files?.[0] || null)} />
          <span className="tag">Gemini makes a new image with different styling, not a copy.</span></div>
        <div className="row">
          <button className="primary" onClick={genImage} disabled={busy === 'image'}>{busy === 'image' ? 'Generating…' : 'Generate image'}</button>
          <label className="line filebtn">{busy === 'upload' ? 'Uploading…' : 'Upload my own'}
            <input type="file" accept="image/*" hidden onChange={(e) => upload(e.target.files?.[0])} /></label>
        </div>
      </section>

      <section className="sec">
        <h2>Title and description</h2>
        <div className="row"><button className="line" onClick={writeSeo} disabled={busy === 'seo'}>{busy === 'seo' ? 'Writing…' : 'Write with Gemini'}</button></div>
        <div className="field"><label htmlFor="t">Title</label>
          <input id="t" type="text" value={f.title} maxLength={100} onChange={(e) => set('title', e.target.value)} />
          <span className="count">{f.title.length}/100</span></div>
        <div className="field"><label htmlFor="d">Description</label>
          <textarea id="d" value={f.description} maxLength={500} onChange={(e) => set('description', e.target.value)} />
          <span className="count">{f.description.length}/500</span></div>
        <div className="field"><label htmlFor="b">Board</label>
          <select id="b" value={f.boardId} onChange={(e) => setF((p) => ({ ...p, boardId: e.target.value, sectionId: '' }))}>
            <option value="">Choose a board</option>{boards.map((b) => <option key={b.id} value={b.id}>{b.name}</option>)}</select></div>
        {board?.sections.length > 0 && (
          <div className="field"><label htmlFor="sec">Section</label>
            <select id="sec" value={f.sectionId} onChange={(e) => set('sectionId', e.target.value)}>
              <option value="">No section</option>{board.sections.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}</select></div>
        )}
      </section>

      <section className="sec">
        <h2>Posting details</h2>
        <div className="field"><label htmlFor="date">Post on</label><input id="date" type="date" value={f.date} onChange={(e) => set('date', e.target.value)} /></div>
        <div className="field"><label htmlFor="time">Time (optional, in your time zone)</label><input id="time" type="time" value={f.time} onChange={(e) => set('time', e.target.value)} /></div>
        <div className="field"><label htmlFor="dest">Destination link (optional)</label>
          <input id="dest" type="url" value={f.dest} onChange={(e) => set('dest', e.target.value)} placeholder="https://" /></div>
      </section>

      {msg && <p className="note" role="status" key={msg}>{msg}</p>}
      <p className={missing.length ? 'tag err' : 'tag ok'}>{missing.length ? `Still needed before it can be posted: ${missing.join(', ')}. You can still save it as a draft.` : 'Everything is filled in. This pin will be ready to post.'}</p>
      <div className="row"><button className="primary" onClick={save} disabled={busy === 'save'}>{busy === 'save' ? 'Saving…' : 'Save pin'}</button></div>
    </>
  );
}
