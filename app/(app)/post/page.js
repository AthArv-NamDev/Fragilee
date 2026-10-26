'use client';
import Link from 'next/link';
import { useEffect, useMemo, useRef, useState } from 'react';
import { supabaseBrowser } from '@/lib/supabase/client';
import { loadBoards, signedUrls, copyText } from '@/lib/data';
import { iso, pretty } from '@/lib/dates';
import { getTimes } from '@/lib/times';

const slug = (t) => (t || 'pin').toLowerCase().replace(/[^a-z0-9]+/g, '-').slice(0, 40) || 'pin';

export default function PostMode() {
  const s = useMemo(() => supabaseBrowser(), []);
  const today = useMemo(() => iso(new Date()), []);
  const [all, setAll] = useState([]);
  const [boards, setBoards] = useState([]);
  const [urls, setUrls] = useState({});
  const [scope, setScope] = useState('today');
  const [ticks, setTicks] = useState({});
  const [posted, setPosted] = useState(0);
  const [skipped, setSkipped] = useState([]);
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(true);
  const file = useRef(null);

  useEffect(() => {
    (async () => {
      const [p, b] = await Promise.all([
        s.from('pins').select('*').in('status', ['optimized', 'scheduled']),
        loadBoards(s),
      ]);
      if (p.error) setMsg(p.error.message);
      const rows = (p.data || []).sort((a, b2) => (a.scheduled_for || '9999').localeCompare(b2.scheduled_for || '9999'));
      setAll(rows);
      setBoards(b);
      setUrls(await signedUrls(s, rows.map((x) => x.image_path)));
      if (!rows.some((x) => x.scheduled_for && x.scheduled_for <= today)) setScope('all');
      setLoading(false);
    })();
  }, [s, today]);

  const list = useMemo(() => {
    const base = scope === 'today' ? all.filter((x) => x.scheduled_for && x.scheduled_for <= today) : all;
    return [...base.filter((x) => !skipped.includes(x.id)), ...base.filter((x) => skipped.includes(x.id))];
  }, [all, scope, today, skipped]);
  const pin = list[0];
  const total = posted + list.length;

  // Pre-load the image so the share sheet opens instantly (browsers need a fresh tap)
  useEffect(() => {
    file.current = null;
    setTicks({});
    const url = pin && urls[pin.image_path];
    if (!url) return;
    let live = true;
    (async () => {
      try {
        const blob = await (await fetch(url)).blob();
        if (!live) return;
        const ext = (blob.type.split('/')[1] || 'jpg').replace('jpeg', 'jpg');
        file.current = new File([blob], `${slug(pin.title)}.${ext}`, { type: blob.type });
      } catch {}
    })();
    return () => { live = false; };
  }, [pin?.id, urls]); // eslint-disable-line react-hooks/exhaustive-deps

  const tick = (k) => setTicks((t) => ({ ...t, [k]: true }));
  const where = () => {
    const b = boards.find((x) => x.id === pin.board_id);
    const sec = b?.sections.find((x) => x.id === pin.section_id);
    return b ? (sec ? `${b.name}, section: ${sec.name}` : b.name) : 'Pick a board';
  };

  async function saveImage() {
    const ext = pin.image_path.split('.').pop();
    const { data, error } = await s.storage.from('pins').createSignedUrl(pin.image_path, 300, { download: `${slug(pin.title)}.${ext}` });
    if (error) return setMsg(error.message);
    tick('image');
    location.href = data.signedUrl;
  }
  async function shareImage() {
    const f = file.current;
    if (f && navigator.canShare?.({ files: [f] })) {
      try { await navigator.share({ files: [f] }); tick('image'); return; }
      catch (e) { if (e.name === 'AbortError') return; }
    }
    setMsg('Sharing is not available here, so the image is downloading instead.');
    saveImage();
  }
  async function copy(k, text) {
    setMsg((await copyText(text || '')) ? '' : 'Could not copy. Press and hold the text to copy it by hand.');
    tick(k);
  }
  async function markPosted() {
    const { error } = await s.from('pins').update({ status: 'posted', posted_at: new Date().toISOString() }).eq('id', pin.id);
    if (error) return setMsg(error.message);
    setAll((p) => p.filter((x) => x.id !== pin.id));
    setPosted((n) => n + 1);
    setMsg('');
  }

  if (loading) return <p className="muted">Getting your pins ready…</p>;

  const scopeChips = (
    <div className="chips">
      <button className="chip" aria-pressed={scope === 'today'} onClick={() => setScope('today')}>Due today</button>
      <button className="chip" aria-pressed={scope === 'all'} onClick={() => setScope('all')}>All ready pins</button>
    </div>
  );

  if (!pin) {
    return (
      <>
        <h1>{posted ? 'All posted' : 'Nothing to post'}</h1>
        <p>{posted ? `You posted ${posted} pin${posted > 1 ? 's' : ''} this session. Nice work.` : scope === 'today' ? 'No pins are due today.' : 'No ready pins yet. Finish some in the pin maker.'}</p>
        {scopeChips}
        <div className="row sec"><Link className="primary" href="/maker">Make a pin</Link><Link className="line" href="/queue">Open queue</Link></div>
      </>
    );
  }

  return (
    <>
      <p className="tag">Pin {posted + 1} of {total}{pin.scheduled_for ? `, planned for ${pretty(pin.scheduled_for)}${getTimes()[pin.id] ? ` at ${getTimes()[pin.id]}` : ''}` : ''}</p>
      <div className="progress" aria-hidden="true"><span style={{ width: `${(posted / total) * 100}%` }} /></div>
      <h1>{pin.title || 'Untitled pin'}</h1>
      {scopeChips}
      <ol className="steps">
        <li className={ticks.image ? 'done' : ''}>
          <h3>Image</h3>
          {urls[pin.image_path] && <img className="step-img" src={urls[pin.image_path]} alt="" />}
          <div className="row">
            <button className="primary" onClick={shareImage}>Share to Pinterest</button>
            <button className="line" onClick={saveImage}>Save to phone</button>
          </div>
          <p className="tag">Share opens your phone share sheet. Choose Pinterest and the image is attached.</p>
        </li>
        <li className={ticks.title ? 'done' : ''}>
          <h3>Title</h3>
          <p className="copytext">{pin.title}</p>
          <div><button className="line" onClick={() => copy('title', pin.title)}>Copy title</button></div>
        </li>
        <li className={ticks.desc ? 'done' : ''}>
          <h3>Description</h3>
          <p className="copytext clamp">{pin.description}</p>
          <div><button className="line" onClick={() => copy('desc', pin.description)}>Copy description</button></div>
        </li>
        {pin.destination_url && (
          <li className={ticks.link ? 'done' : ''}>
            <h3>Link</h3>
            <p className="copytext">{pin.destination_url}</p>
            <div><button className="line" onClick={() => copy('link', pin.destination_url)}>Copy link</button></div>
          </li>
        )}
        <li className={ticks.board ? 'done' : ''}>
          <h3>Board</h3>
          <p className="copytext">{where()}</p>
          <div><button className="quiet" onClick={() => tick('board')}>Done, I chose it</button></div>
        </li>
      </ol>
      {msg && <p className="note" role="status" key={msg}>{msg}</p>}
      <div className="bar">
        <button className="primary" onClick={markPosted}>Posted, next pin</button>
        {list.length > 1 && <button className="quiet" onClick={() => setSkipped((p) => [...p, pin.id])}>Skip for now</button>}
        <a className="quiet" href="https://www.pinterest.com/pin-creation-tool/" target="_blank" rel="noopener noreferrer">Open Pinterest</a>
      </div>
    </>
  );
}
