import { handle, fail } from '@/lib/ai-route';

export const maxDuration = 60;
const MONTH = 60 * 60 * 24 * 30;

// Gives each chosen pin a web link Pinterest can fetch.
// Prefers a permanent public copy; if that bucket is not set up, uses a 30 day private link instead.
export const POST = (req) =>
  handle(req, async ({ body, user, supabase }) => {
    const ids = (Array.isArray(body.ids) ? body.ids : []).slice(0, 50).map(String);
    if (!ids.length) throw fail('No pins selected.');
    const { data: pins, error } = await supabase.from('pins').select('id,image_path').in('id', ids);
    if (error) throw fail(error.message, 500);

    const urls = {};
    let publicOk = true;
    for (const p of pins || []) {
      if (!p.image_path) continue;
      if (publicOk) {
        const { data: blob } = await supabase.storage.from('pins').download(p.image_path);
        if (blob) {
          const ext = (p.image_path.split('.').pop() || 'jpg').toLowerCase();
          const path = `${user.id}/${p.id}-${Date.now()}.${ext}`;
          const { error: upErr } = await supabase.storage
            .from('pin-images')
            .upload(path, blob, { contentType: blob.type || (ext === 'png' ? 'image/png' : 'image/jpeg') });
          if (!upErr) { urls[p.id] = supabase.storage.from('pin-images').getPublicUrl(path).data.publicUrl; continue; }
        }
        publicOk = false;
      }
      const { data, error: signErr } = await supabase.storage.from('pins').createSignedUrl(p.image_path, MONTH);
      if (signErr || !data?.signedUrl) throw fail(`Could not make a link for an image: ${signErr?.message || 'unknown error'}`, 500);
      urls[p.id] = data.signedUrl;
    }
    return { urls, mode: publicOk ? 'public' : 'private-30-days' };
  });
