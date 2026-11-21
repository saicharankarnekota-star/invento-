/**
 * INVENTO AI - Supabase Client SDK Integration
 * Provides unified Authentication, Object Storage, and Database access for the frontend.
 */
import { createClient } from 'https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2/+esm';

export const SUPABASE_URL = 'https://ezfneigycsbtgooijuiz.supabase.co';
export const SUPABASE_PUBLISHABLE_KEY = 'sb_publishable_Ku971fGXam8ruMdqpKpFxg_fu925BrX';

// Initialize Supabase Client
export const supabase = createClient(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, {
  auth: {
    persistSession: true,
    autoRefreshToken: true,
    detectSessionInUrl: true
  }
});

/**
 * 1. SUPABASE AUTHENTICATION
 */

// Sign in with email and password
export async function signIn(email, password) {
  try {
    const { data, error } = await supabase.auth.signInWithPassword({
      email: email.trim(),
      password: password
    });
    if (error) throw error;
    console.log('[Supabase Auth] Signed in successfully as:', data.user.email);
    return { success: true, user: data.user, session: data.session };
  } catch (err) {
    console.warn('[Supabase Auth] Sign in error:', err.message);
    return { success: false, error: err.message };
  }
}

// Sign up new user
export async function signUp(email, password, fullName = '', role = 'cashier') {
  try {
    const { data, error } = await supabase.auth.signUp({
      email: email.trim(),
      password: password,
      options: {
        data: {
          full_name: fullName,
          role: role
        }
      }
    });
    if (error) throw error;
    return { success: true, user: data.user, session: data.session };
  } catch (err) {
    console.warn('[Supabase Auth] Sign up error:', err.message);
    return { success: false, error: err.message };
  }
}

// Sign out
export async function signOut() {
  try {
    const { error } = await supabase.auth.signOut();
    if (error) throw error;
    return { success: true };
  } catch (err) {
    return { success: false, error: err.message };
  }
}

// Get current logged-in user
export async function getCurrentUser() {
  const { data: { user } } = await supabase.auth.getUser();
  return user;
}

/**
 * 2. SUPABASE STORAGE
 */

// Upload a product image to 'invento-products' bucket
export async function uploadProductImage(file, customFilename = null) {
  try {
    const fileExt = file.name.split('.').pop();
    const fileName = customFilename || `prod_${Date.now()}_${Math.random().toString(36).substring(2, 8)}.${fileExt}`;
    const filePath = `${fileName}`;

    const { data, error } = await supabase.storage
      .from('invento-products')
      .upload(filePath, file, {
        cacheControl: '3600',
        upsert: true
      });

    if (error) throw error;

    const { data: { publicUrl } } = supabase.storage
      .from('invento-products')
      .getPublicUrl(filePath);

    return { success: true, filePath, publicUrl };
  } catch (err) {
    console.error('[Supabase Storage] Product upload error:', err);
    return { success: false, error: err.message };
  }
}

// Upload a shelf scan capture to 'invento-scans' bucket
export async function uploadScanImage(file, customFilename = null) {
  try {
    const fileExt = file.name ? file.name.split('.').pop() : 'jpg';
    const fileName = customFilename || `scan_${Date.now()}.${fileExt}`;
    const filePath = `${fileName}`;

    const { data, error } = await supabase.storage
      .from('invento-scans')
      .upload(filePath, file, {
        cacheControl: '3600',
        upsert: true
      });

    if (error) throw error;

    const { data: { publicUrl } } = supabase.storage
      .from('invento-scans')
      .getPublicUrl(filePath);

    return { success: true, filePath, publicUrl };
  } catch (err) {
    console.error('[Supabase Storage] Scan upload error:', err);
    return { success: false, error: err.message };
  }
}

/**
 * 3. SUPABASE DATABASE (REALTIME READS)
 */

// Fetch active products list directly from Supabase
export async function getLiveProducts() {
  try {
    const { data, error } = await supabase
      .from('products')
      .select('*')
      .order('name');
    if (error) throw error;
    return { success: true, products: data };
  } catch (err) {
    console.error('[Supabase DB] Query error:', err);
    return { success: false, error: err.message };
  }
}

// Health check and connectivity diagnostics
export async function testSupabaseConnection() {
  try {
    const { data, error } = await supabase.auth.getSession();
    if (error) {
      console.warn('[Supabase] Auth check returned notice:', error.message);
      return { success: false, error: error.message };
    }
    console.log('[Supabase] Connected to project: ezfneigycsbtgooijuiz');
    return { success: true, project: 'ezfneigycsbtgooijuiz' };
  } catch (err) {
    console.error('[Supabase] Connection failed:', err);
    return { success: false, error: err.message };
  }
}

// Expose on window for interactive browser use
if (typeof window !== 'undefined') {
  window.inventoSupabase = {
    client: supabase,
    signIn,
    signUp,
    signOut,
    getCurrentUser,
    uploadProductImage,
    uploadScanImage,
    getLiveProducts,
    test: testSupabaseConnection,
    url: SUPABASE_URL
  };
}
