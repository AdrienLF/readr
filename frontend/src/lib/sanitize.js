import DOMPurify from 'dompurify';

/**
 * Sanitize HTML to prevent XSS from untrusted feed content.
 * Allows standard article markup but strips scripts, event handlers, etc.
 */
export function sanitize(html) {
  return DOMPurify.sanitize(html, {
    ADD_ATTR: ['target'],  // allow target="_blank" on links
  });
}
