'use client';
import { useMemo, useState } from 'react';
import { post } from '@/lib/api';
import { toUtcStamp, localDate, pretty } from '@/lib/dates';

const HEAD = ['Title', 'Media URL', 'Pinterest board', 'Description', 'Link', 'Publish date', 'Keywords'];
const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
const isUrl = (v) => { try { const u = new URL(v); return u.protocol === 'http:' || u.protocol === 'https:'; } catch { return false; } };
const hhmm = (m) => `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;

export default function ExportPanel({ pins, boards, patch, setMsg, times, changeTime }) {
  const [open, setOpen] = useState(false);
  const [withSections, setWithSections] = useState(false);
  const [checked, setChecked] = useState(false);
  const [start, setStart] = useState('10:00');
  const [gap, setGap] = useState(90);
  const [busy, setBusy] = useState(false);
  const [done, setDone] = useState(null);
  const tz = typeof Intl !== 'undefined' ? Intl.DateTimeFormat().resolvedOptions().timeZone : 'your time zone';

  const rows = useMemo(() => {
    const list = pins.filter((p) => ['optimized', 'scheduled'].includes(p.status)).map((p) => {
      const b = boards.find((x) => x.id === p.board_id);
      const sec = withSections ? b?.sections.find((x) => x.id === p.section_id) : null;
      const errors = [];
      const warns = [];
      if (!p.image_path) errors.push('no image');
      if (!p.title) errors.push('no title');
      if (!b) errors.push('no board');
      if (p.title && p.title.length > 100) errors.push('title is over 100 characters');
      if (p.description && p.description.length > 500) errors.push('description is over 500 characters');
      if (p.destination_url && !isUrl(p.destination_url)) errors.push('the link is not a valid web address');
      if (!p.description) warns.push('no description');
      if (!p.scheduled_for) warns.push('no date, so it publishes straight away');
      else if (!times[p.id]) warns.push('no time, so Pinterest uses the time you upload the file');
      else if (localDate(p.scheduled_for, times[p.id]) < new Date()) warns.push('that time has passed, so it publishes straight away');
      return { p, board: b ? (sec ? `${b.name}/${sec.name}` : b.name) : '', stamp: toUtcStamp(p.scheduled_for, times[p.id]), errors, warns };
    });
    const count = {};
    list.forEach((r) => { if (times[r.p.id]) count[r.stamp] = (count[r.stamp] || 0) + 1; });
    list.forEach((r) => { if (times[r.p.id] && count[r.stamp] > 1) r.warns.push('same date and time as another pin'); });
    return list.sort((a, b) => (a.stamp || '9999').localeCompare(b.stamp || '9999'));
  }, [pins, boards, withSections, times]);

  const ok = rows.filter((r) => !r.errors.length).slice(0, 200);
  const blocked = rows.filter((r) => r.errors.length);
  const boardNames = [...new Set(ok.map((r) => r.board))];

  async function autoSpace() {
    const [h, m] = start.split(':').map(Number);
    const s0 = h * 60 + m;
    const byDate = {};
    ok.filter((r) => r.p.scheduled_for).forEach((r) => (byDate[r.p.scheduled_for] ||= []).push(r.p));
    let n = 0;
    for (const list of Object.values(byDate)) {
      const g = list.length > 1 ? Math.max(1, Math.min(Number(gap) || 90, Math.floor((1380 - s0) / (list.length - 1)))) : 0;
      for (const [i, p] of list.entries()) {
        changeTime(p.id, hhmm(Math.min(s0 + i * g, 1439)));
        n++;
      }
    }
    setMsg(n ? `Set times for ${n} pin${n > 1 ? 's' : ''}.` : 'No dated pins to space out. Give the pins a date first.');
  }

  async function download() {
    if (!ok.length) return;
    setBusy(true); setMsg('');
    try {
      const d = await post('/api/export/images', { ids: ok.map((r) => r.p.id) });
      const out = ok.filter((r) => d.urls[r.p.id]);
      const csv = [HEAD, ...out.map((r) => [r.p.title, d.urls[r.p.id], r.board, r.p.description || '', r.p.destination_url || '', r.stamp, ''])]
        .map((row) => row.map(esc).join(',')).join('\n');
      const url = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
      const a = document.createElement('a');
      a.href = url; a.download = `pinterest-bulk-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(a); a.click(); a.remove(); URL.revokeObjectURL(url);
      setDone({ ids: out.map((r) => r.p.id), count: out.length });
    } catch (e) { setMsg(e.message); }
    setBusy(false);
  }
  async function markPosted() {
    for (const id of done.ids) await patch(id, { status: 'posted', posted_at: new Date().toISOString() });
    setDone(null); setOpen(false); setMsg('Marked as posted.');
  }

  return (
    <section className="sec">
      <h2>Upload many pins at once</h2>
      <p className="muted">Review everything, then download a CSV for Pinterest Bulk create Pins (desktop, business account, up to 200 pins).</p>
      {!open ? (
        <div className="row"><button className="line" onClick={() => { setOpen(true); setChecked(false); }}>Review and download CSV</button></div>
      ) : (
        <>
          <div className="row">
            <label className="tag">First pin at <input type="time" value={start} onChange={(e) => setStart(e.target.value)} /></label>
            <label className="tag">every <input type="number" min="1" max="600" value={gap} onChange={(e) => setGap(e.target.value)} style={{ width: 80 }} /> minutes</label>
            <button className="line" onClick={autoSpace}>Space out times on each day</button>
          </div>
          <label className="row"><input type="checkbox" checked={withSections} onChange={(e) => { setWithSections(e.target.checked); setChecked(false); }} /> Include sections (they must already exist with the same names)</label>
          <p className="tag">Times are in your device time zone ({tz}). The file converts them to UTC, which is what Pinterest expects.</p>

          <ul className="list">
            {rows.map((r) => (
              <li className="item" key={r.p.id}>
                <h3>{r.p.title || 'Untitled'}</h3>
                <p className="tag">{r.board || 'No board'}</p>
                <p className="tag">
                  {r.p.scheduled_for ? `${pretty(r.p.scheduled_for)}${times[r.p.id] ? ` at ${times[r.p.id].slice(0, 5)}` : ''}` : 'No date'}
                  {r.stamp ? ` | In the file: ${r.stamp}${times[r.p.id] ? ' (UTC)' : ''}` : ''}
                </p>
                {r.errors.length > 0 && <p className="tag err">Left out: {r.errors.join(', ')}</p>}
                {r.warns.length > 0 && <p className="tag">Note: {r.warns.join('; ')}</p>}
              </li>
            ))}
          </ul>
          {rows.length === 0 && <p className="muted">No ready pins yet.</p>}
          {blocked.length > 0 && <p className="tag err">{blocked.length} pin{blocked.length > 1 ? 's are' : ' is'} left out of the file until fixed.</p>}

          {ok.length > 0 && (
            <div className="panel">
              <p><strong>Boards in this file:</strong> {boardNames.join('; ')}</p>
              <p className="tag">If a name differs from your Pinterest board even slightly, Pinterest creates a new board.</p>
              <label className="row"><input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} /> I checked each name against my Pinterest boards</label>
            </div>
          )}
          <div className="row">
            <button className="primary" onClick={download} disabled={!ok.length || !checked || busy}>{busy ? 'Preparing…' : `Download CSV (${ok.length} pin${ok.length === 1 ? '' : 's'})`}</button>
            <button className="quiet" onClick={() => setOpen(false)}>Close</button>
          </div>
        </>
      )}
      {done && (
        <div className="panel">
          <p><strong>{done.count} pins are in the file you downloaded.</strong> Upload it in Pinterest, then check Scheduled pins.</p>
          <div className="row"><button className="primary" onClick={markPosted}>I uploaded it, mark these posted</button><button className="quiet" onClick={() => setDone(null)}>Not yet</button></div>
        </div>
      )}
    </section>
  );
}
