const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * Converts a relative asset path (e.g. "/uploads/parts/...") into an absolute URL
 * pointing to the backend API origin.
 */
export function getAssetUrl(imageUrl: string | null | undefined): string | null {
  if (!imageUrl || !imageUrl.trim()) {
    return null;
  }
  const trimmed = imageUrl.trim();
  if (trimmed.startsWith('http://') || trimmed.startsWith('https://')) {
    return trimmed;
  }
  // Strip trailing /api and trailing slashes to obtain the server origin
  const apiOrigin = API_BASE_URL.replace(/\/api\/?$/, '').replace(/\/+$/, '');
  const cleanPath = trimmed.startsWith('/') ? trimmed : `/${trimmed}`;
  return `${apiOrigin}${cleanPath}`;
}

