// Copyright (c) 2026 Lumen Solutions. All rights reserved.
// SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
// Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
/**
 * The site's visual identity.
 *
 * One saved look — a name, a logo, a letterhead and a default theme — that
 * every dashboard and every report follows unless it sets its own. It travels
 * with the page at load rather than being fetched, so a dashboard paints in the
 * organization's colors on the first frame instead of flashing the app's blue.
 */
import { computed, reactive } from 'vue'
import { call } from 'frappe-ui'

export const brand = reactive({
  organization: '',
  logo: '',
  letterhead: '',
  footer_text: '',
  theme: {},
  can_manage: false,
})

function adopt(next) {
  if (!next || typeof next !== 'object') return
  brand.organization = String(next.organization || '')
  brand.logo = String(next.logo || '')
  brand.letterhead = String(next.letterhead || '')
  brand.footer_text = String(next.footer_text || '')
  brand.theme = next.theme && typeof next.theme === 'object' ? { ...next.theme } : {}
  brand.can_manage = Boolean(next.can_manage)
}

// handed over by the page; absent when the SPA runs off the Vite dev server
adopt(typeof window !== 'undefined' ? window.lumen_brand : null)

/** The theme every dashboard falls back to, field by field. */
export const brandTheme = computed(() => brand.theme || {})

export async function loadIdentity() {
  adopt(await call('lumen_reports.brand.get_identity'))
  return brand
}

export async function saveIdentity(payload) {
  adopt(await call('lumen_reports.brand.save_identity', { payload }))
  return brand
}

export function extractColors(fileUrl, useAi = true) {
  return call('lumen_reports.brand.extract_colors', { file_url: fileUrl, use_ai: useAi ? 1 : 0 })
}

/**
 * Put an image on the site and hand back its public path. Print reads images
 * off the disk and refuses anything private, so these are never private files.
 */
export async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file, file.name)
  form.append('is_private', '0')
  form.append('folder', 'Home/Attachments')

  const response = await fetch('/api/method/upload_file', {
    method: 'POST',
    headers: { 'X-Frappe-CSRF-Token': window.csrf_token || '' },
    body: form,
  })
  let payload = null
  try {
    payload = await response.json()
  } catch {
    /* an error page rather than JSON */
  }
  if (!response.ok || !payload?.message?.file_url) {
    throw new Error(serverMessage(payload) || 'Upload failed')
  }
  return String(payload.message.file_url)
}

/**
 * The one readable line out of a Frappe failure, whichever shape it arrives in:
 * a thrown frappe-ui error, or the raw JSON body of a fetch.
 */
export function serverMessage(failure) {
  const strip = (text) => String(text || '').replace(/<[^>]+>/g, '').trim()

  if (Array.isArray(failure?.messages) && failure.messages.length) return strip(failure.messages[0])
  try {
    const messages = JSON.parse(failure?._server_messages || '[]')
    if (messages.length) return strip(JSON.parse(messages[0]).message)
  } catch {
    /* not a server-message payload */
  }
  return strip(failure?.exception || failure?.message)
}
