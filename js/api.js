// Ghost Frame — API client (Supabase JS direct, no backend required)

const SUPABASE_URL  = 'https://zdtdajlghningkcimeqa.supabase.co';
const SUPABASE_ANON = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InpkdGRhamxnaG5pbmdrY2ltZXFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODk5ODMwMTgsImV4cCI6MjEwNTU1OTAxOH0._NehgIJkJzIwkYQc5btVyAyOUUjnFIeYfOR1B1prQ_I';

// Lazy-init Supabase client (supabase-js loaded via CDN on each page)
function getSB() {
  if (window._ghostSB) return window._ghostSB;
  if (typeof supabase === 'undefined') throw new Error('Supabase JS not loaded');
  window._ghostSB = supabase.createClient(SUPABASE_URL, SUPABASE_ANON);
  return window._ghostSB;
}

// Get current user ID (returns null if not logged in)
async function getUID() {
  const sb = getSB();
  const { data: { session } } = await sb.auth.getSession();
  return session?.user?.id || null;
}

// ── Projects ──────────────────────────────────────────────────────────────
export const projects = {
  async list() {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { data, error } = await getSB()
      .from('projects')
      .select('*')
      .eq('user_id', uid)
      .order('created_at', { ascending: false });
    if (error) throw new Error(error.message);
    return data;
  },

  async get(id) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { data, error } = await getSB()
      .from('projects')
      .select('*')
      .eq('id', id)
      .eq('user_id', uid)
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async create(payload) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { data, error } = await getSB()
      .from('projects')
      .insert({ ...payload, user_id: uid })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async update(id, payload) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { data, error } = await getSB()
      .from('projects')
      .update(payload)
      .eq('id', id)
      .eq('user_id', uid)
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async remove(id) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { error } = await getSB()
      .from('projects')
      .delete()
      .eq('id', id)
      .eq('user_id', uid);
    if (error) throw new Error(error.message);
    return null;
  },

  // Upload image blob and create a project record
  async uploadResult(blob, title, effectUsed) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const sb = getSB();
    const ext  = 'png';
    const path = `${uid}/${Date.now()}.${ext}`;
    const { error: upErr } = await sb.storage
      .from('results')
      .upload(path, blob, { contentType: 'image/png', upsert: false });
    if (upErr) throw new Error(upErr.message);
    const { data: { publicUrl } } = sb.storage.from('results').getPublicUrl(path);
    const { data, error } = await sb
      .from('projects')
      .insert({
        user_id:    uid,
        title:      title || 'Untitled',
        effect_used: effectUsed || null,
        result_url: publicUrl,
      })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data;
  },
};

// ── Discover ──────────────────────────────────────────────────────────────
export const discover = {
  async list({ page = 1, limit = 20, tag, effect } = {}) {
    const sb  = getSB();
    const uid = await getUID();
    const offset = (page - 1) * limit;

    let q = sb.from('discover_posts')
      .select('*, profiles(username, avatar_url)')
      .order('created_at', { ascending: false })
      .range(offset, offset + limit - 1);

    if (tag)    q = q.contains('tags', [tag]);
    if (effect) q = q.eq('effect_used', effect);

    const { data: posts, error } = await q;
    if (error) throw new Error(error.message);

    if (uid && posts?.length) {
      const ids = posts.map(p => p.id);
      const { data: likes } = await sb
        .from('discover_likes')
        .select('post_id')
        .eq('user_id', uid)
        .in('post_id', ids);
      const likedSet = new Set((likes || []).map(l => l.post_id));
      posts.forEach(p => { p.liked = likedSet.has(p.id); });
    }
    return { posts: posts || [], page, limit };
  },

  async get(id) {
    const { data, error } = await getSB()
      .from('discover_posts')
      .select('*, profiles(username, avatar_url)')
      .eq('id', id)
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async create(payload) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { data, error } = await getSB()
      .from('discover_posts')
      .insert({ ...payload, user_id: uid })
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async remove(id) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { error } = await getSB()
      .from('discover_posts')
      .delete()
      .eq('id', id)
      .eq('user_id', uid);
    if (error) throw new Error(error.message);
    return null;
  },

  async like(id) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const sb = getSB();
    const { data: existing } = await sb
      .from('discover_likes')
      .select('id')
      .eq('user_id', uid)
      .eq('post_id', id)
      .single();

    if (existing) {
      await sb.from('discover_likes').delete().eq('user_id', uid).eq('post_id', id);
      await sb.rpc('decrement_likes', { post_id: id });
      return { liked: false };
    } else {
      await sb.from('discover_likes').insert({ user_id: uid, post_id: id });
      await sb.rpc('increment_likes', { post_id: id });
      return { liked: true };
    }
  },
};

// ── Process (AI effects — needs Python server; gracefully degrade) ─────────
export const process = {
  // AI_BASE can be set to a Render/Railway backend URL when available
  _base: window.AI_BACKEND_URL || null,

  async run(effect, file, save = false) {
    if (!this._base) throw new Error('AI backend not configured');
    const token = await (async () => {
      const { data: { session } } = await getSB().auth.getSession();
      return session?.access_token || null;
    })();
    const form = new FormData();
    form.append('file', file);
    form.append('save', save);
    const res = await fetch(`${this._base}/api/process/${effect}`, {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || 'Processing failed');
    }
    return res;
  },
};

// ── Profile ───────────────────────────────────────────────────────────────
export const profile = {
  async me() {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const sb = getSB();
    const { data, error } = await sb
      .from('profiles')
      .select('*')
      .eq('id', uid)
      .single();
    if (error && error.code === 'PGRST116') {
      // Row not found — auto-create
      const { data: created } = await sb.from('profiles').insert({ id: uid }).select().single();
      return created || { id: uid };
    }
    if (error) throw new Error(error.message);
    return data;
  },

  async update(payload) {
    const uid = await getUID();
    if (!uid) throw new Error('Not authenticated');
    const { data, error } = await getSB()
      .from('profiles')
      .update(payload)
      .eq('id', uid)
      .select()
      .single();
    if (error) throw new Error(error.message);
    return data;
  },

  async get(username) {
    const { data, error } = await getSB()
      .from('profiles')
      .select('*')
      .eq('username', username)
      .single();
    if (error) throw new Error(error.message);
    return data;
  },
};

export default { projects, discover, process, profile };
