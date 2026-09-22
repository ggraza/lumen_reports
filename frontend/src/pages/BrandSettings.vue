<!-- Copyright (c) 2026 Lumen Solutions. All rights reserved.
     SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
     Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions. -->
<template>
  <main class="wrap">
    <div class="top">
      <div>
        <h1>{{ t('Visual identity') }}</h1>
        <p>{{ t('One saved look. Every dashboard and every report follows it unless it sets its own.') }}</p>
      </div>
      <router-link to="/" class="lbtn">{{ t('Back to dashboards') }}</router-link>
    </div>

    <p v-if="!brand.can_manage" class="err">
      {{ t('Only a Lumen Manager can change the visual identity. Ask your administrator.') }}
    </p>

    <div v-else class="cols">
      <section class="col">
        <div class="panel">
          <div class="panel-h">
            <div class="t">{{ t('Identity') }}</div>
            <div class="s">{{ t('What a printed report says it comes from') }}</div>
          </div>
          <div class="panel-b stack">
            <div class="lfield">
              <label>{{ t('Organization name') }}</label>
              <input
                v-model="form.organization"
                type="text"
                :placeholder="t('Blank uses the Company on this site')"
                maxlength="140"
              />
            </div>

            <div v-for="field in IMAGE_FIELDS" :key="field.key" class="imgfield">
              <label class="eyebrow">{{ t(field.label) }}</label>
              <p class="hint">{{ t(field.hint) }}</p>

              <div v-if="form[field.key]" class="shot" :class="field.key">
                <img :src="form[field.key]" alt="" />
              </div>

              <div class="btns">
                <button class="lbtn sm" :disabled="busy !== ''" @click="choose(field.key)">
                  {{ form[field.key] ? t('Replace') : t('Upload') }}
                </button>
                <button
                  v-if="form[field.key]"
                  class="lbtn sm"
                  :disabled="busy !== ''"
                  @click="extract(field.key)"
                >
                  {{ t('Pick colors from this image') }}
                </button>
                <button
                  v-if="form[field.key]"
                  class="lbtn sm danger"
                  :disabled="busy !== ''"
                  @click="form[field.key] = ''"
                >
                  {{ t('Remove') }}
                </button>
              </div>
              <input
                :ref="(el) => (inputs[field.key] = el)"
                type="file"
                accept="image/png,image/jpeg,image/webp"
                hidden
                @change="onFile(field.key, $event)"
              />
            </div>

            <div class="lfield">
              <label>{{ t('Report footer line') }}</label>
              <input
                v-model="form.footer_text"
                type="text"
                :placeholder="t('For example: Confidential, for internal use')"
                maxlength="120"
              />
              <p class="hint">{{ t('Printed in the middle of the page foot, beside the Lumen Reports credit.') }}</p>
            </div>

            <div class="lfield">
              <label>{{ t('Report font, Latin') }}</label>
              <select v-model="form.report_font">
                <option v-for="f in LATIN_FONTS" :key="f" :value="f">{{ f }}</option>
              </select>
            </div>

            <div class="lfield">
              <label>{{ t('Report font, Arabic') }}</label>
              <select v-model="form.report_font_ar">
                <option v-for="f in ARABIC_FONTS" :key="f" :value="f">{{ f }}</option>
              </select>
              <p class="fontspec" dir="rtl" :style="{ fontFamily: form.report_font_ar }">
                الإجمالي المستحق · تقرير المبيعات · 1,090,597
              </p>
              <p class="hint">
                {{ t('Arabic text in the PDF uses this one. A Latin font has no Arabic letters, so every Arabic line follows this choice.') }}
              </p>
            </div>
          </div>
        </div>

        <div v-if="found" class="panel">
          <div class="panel-h">
            <div class="t">{{ t('Colors found') }}</div>
            <div class="s">
              {{ found.source === 'ai' ? t('Chosen by AI from your identity') : t('Measured from the image') }}
            </div>
          </div>
          <div class="panel-b stack">
            <p v-if="found.note" class="hint">{{ found.note }}</p>
            <p v-if="found.secondary_derived" class="hint">
              {{ t('The image carries one color, so the second was built to sit beside it. Change it if you have a real one.') }}
            </p>

            <div class="pairs">
              <div v-for="slot in ['primary', 'secondary']" :key="slot" class="pair">
                <label class="eyebrow">{{ slot === 'primary' ? t('Primary color') : t('Secondary color') }}</label>
                <div class="swatches">
                  <button
                    v-for="color in found.colors"
                    :key="slot + color"
                    class="sw"
                    :class="{ on: chosen[slot] === color }"
                    :style="{ background: color }"
                    :title="color"
                    @click="chosen[slot] = color"
                  ></button>
                </div>
                <span class="mono hexlabel" dir="ltr">{{ chosen[slot] }}</span>
              </div>
            </div>

            <div class="btns">
              <button class="lbtn primary" @click="applyFound">{{ t('Use these colors') }}</button>
              <button class="lbtn" @click="found = null">{{ t('Cancel') }}</button>
            </div>
          </div>
        </div>

        <div class="panel">
          <div class="panel-h">
            <div class="t">{{ t('Report preview') }}</div>
            <div class="s">{{ t('How the top of a printed report will look') }}</div>
          </div>
          <div class="panel-b">
            <div class="rprev" :style="{ '--accent': accent }">
              <img v-if="form.letterhead" class="lh" :src="form.letterhead" alt="" />
              <div class="rh">
                <img v-if="form.logo" class="lg" :src="form.logo" alt="" />
                <div class="who">
                  <div class="ti">{{ t('Sales Overview') }}</div>
                  <div class="su mono" dir="ltr">2026-09-01 / 2026-09-30</div>
                </div>
                <div class="me">
                  <b dir="auto">{{ form.organization || t('Your organization') }}</b>
                  <div class="mono" dir="ltr">2026-09-21</div>
                </div>
              </div>
              <div class="series">
                <i v-for="(color, i) in previewPalette" :key="i" :style="{ background: color }"></i>
              </div>
              <div class="ft">
                <span>Created by Lumen Reports</span>
                <span v-if="form.footer_text" class="own" dir="auto">{{ form.footer_text }}</span>
                <span class="pg mono" dir="ltr">1 / 3</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <aside class="col side">
        <div class="panel tpwrap">
          <ThemePanel :theme="form.theme" for-brand :closable="false" @apply="onTheme" />
        </div>
      </aside>
    </div>

    <div v-if="brand.can_manage" class="savebar">
      <span v-if="error" class="err inline">{{ error }}</span>
      <span v-else-if="busy" class="note">{{ busy }}</span>
      <span v-else-if="saved" class="note ok">{{ t('Saved. New pages will follow it.') }}</span>
      <span v-else class="note">{{ t('A dashboard with a theme of its own keeps it.') }}</span>
      <span style="flex: 1"></span>
      <button class="lbtn" :disabled="busy !== ''" @click="reset">{{ t('Undo changes') }}</button>
      <button class="lbtn primary" :disabled="busy !== ''" @click="save">{{ t('Save identity') }}</button>
    </div>
  </main>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import ThemePanel from '@/components/builder/ThemePanel.vue'
import { brand, extractColors, saveIdentity, serverMessage, uploadImage } from '@/lib/brand'
import { DEFAULT_THEME, findPreset, themeVars } from '@/lib/dashboardTheme'
import { t } from '@/lib/i18n'
import '@/components/builder/controls.css'

const IMAGE_FIELDS = [
  {
    key: 'logo',
    label: 'Logo',
    hint: 'Printed beside the report title. A PNG or JPG with a transparent or white background reads best.',
  },
  {
    key: 'letterhead',
    label: 'Letterhead',
    hint: 'A full width band printed at the top of the first page, above the title.',
  },
]

const inputs = {}
const busy = ref('')
const error = ref('')
const saved = ref(false)
const found = ref(null)
const chosen = reactive({ primary: '', secondary: '' })

// the faces bundled with the app, mirroring REPORT_FONTS / REPORT_FONTS_AR in brand.py
const LATIN_FONTS = ['Plus Jakarta Sans', 'Inter']
const ARABIC_FONTS = ['IBM Plex Sans Arabic', 'Cairo', 'Tajawal', 'Almarai', 'Noto Naskh Arabic']

function blank() {
  return {
    organization: brand.organization,
    logo: brand.logo,
    letterhead: brand.letterhead,
    footer_text: brand.footer_text,
    report_font: brand.report_font || LATIN_FONTS[0],
    report_font_ar: brand.report_font_ar || ARABIC_FONTS[0],
    theme: { ...DEFAULT_THEME, ...(brand.theme || {}) },
  }
}

const form = reactive(blank())

function reset() {
  Object.assign(form, blank())
  found.value = null
  error.value = ''
}

const accent = computed(() => themeVars(form.theme)['--c1'] || 'var(--blue)')
const previewPalette = computed(() => {
  const vars = themeVars(form.theme)
  const preset = findPreset(form.theme.preset)
  return ['--c1', '--c2', '--c3', '--c4', '--c5'].map(
    (slot) => vars[slot] || preset?.vars[slot] || `var(${slot})`
  )
})

function onTheme(next) {
  form.theme = { ...next }
  saved.value = false
}

function choose(key) {
  error.value = ''
  inputs[key]?.click()
}

async function onFile(key, event) {
  const file = event.target.files?.[0]
  event.target.value = ''
  if (!file) return
  error.value = ''
  saved.value = false
  busy.value = t('Uploading...')
  try {
    form[key] = await uploadImage(file)
  } catch (e) {
    error.value = serverMessage(e) || t('That image could not be uploaded.')
  } finally {
    busy.value = ''
  }
}

async function extract(key) {
  error.value = ''
  busy.value = t('Reading the colors...')
  try {
    const result = await extractColors(form[key], true)
    chosen.primary = result.primary
    chosen.secondary = result.secondary
    found.value = result
  } catch (e) {
    error.value = serverMessage(e) || t('Those colors could not be read.')
  } finally {
    busy.value = ''
  }
}

function applyFound() {
  form.theme = {
    ...form.theme,
    brand: chosen.primary || form.theme.brand,
    secondary: chosen.secondary || form.theme.secondary,
    // a light mark on a dark identity should not land on a white page
    preset: form.theme.preset || found.value?.suggested_preset || '',
  }
  found.value = null
  saved.value = false
}

async function save() {
  error.value = ''
  busy.value = t('Saving...')
  try {
    await saveIdentity({
      organization: form.organization,
      logo: form.logo,
      letterhead: form.letterhead,
      footer_text: form.footer_text,
      report_font: form.report_font,
      report_font_ar: form.report_font_ar,
      theme: form.theme,
    })
    saved.value = true
  } catch (e) {
    error.value = serverMessage(e) || t('That could not be saved.')
  } finally {
    busy.value = ''
  }
}
</script>

<style scoped>
.wrap {
  max-width: 1180px;
  margin: 0 auto;
  padding: 26px 24px 120px;
}
.top {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
}
.top h1 {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--ink);
  letter-spacing: -0.01em;
}
.top p {
  margin: 5px 0 0;
  font-size: 13.5px;
  color: var(--muted);
  font-weight: 500;
  max-width: 62ch;
}
.top .lbtn {
  margin-inline-start: auto;
  flex: none;
  text-decoration: none;
}

.cols {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 18px;
  align-items: start;
}
@media (max-width: 900px) {
  .cols {
    grid-template-columns: minmax(0, 1fr);
  }
}
.col {
  display: flex;
  flex-direction: column;
  gap: 16px;
  min-width: 0;
}
.side {
  position: sticky;
  top: 18px;
}
.tpwrap {
  overflow: hidden;
  padding: 0;
}

.stack {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.eyebrow {
  font-family: var(--mono);
  font-size: 9.5px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
  font-weight: 600;
}
.hint {
  margin: 0;
  font-size: 11.5px;
  line-height: 1.55;
  color: var(--muted);
  font-weight: 500;
}
/* the same faces the PDF prints with, served from the app, so the specimen below the
   picker is the real thing and not the browser's guess */
@font-face {
  font-family: 'IBM Plex Sans Arabic';
  src: url('/assets/lumen_reports/fonts/ibm-plex-sans-arabic-arabic-400-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Cairo';
  src: url('/assets/lumen_reports/fonts/cairo-arabic-400-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Tajawal';
  src: url('/assets/lumen_reports/fonts/tajawal-arabic-400-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Almarai';
  src: url('/assets/lumen_reports/fonts/almarai-arabic-400-normal.woff2') format('woff2');
}
@font-face {
  font-family: 'Noto Naskh Arabic';
  src: url('/assets/lumen_reports/fonts/noto-naskh-arabic-arabic-400-normal.woff2') format('woff2');
}
.fontspec {
  margin: 2px 0 0;
  padding: 10px 12px;
  border: 1px solid var(--border-2);
  border-radius: 10px;
  background: var(--panel);
  color: var(--ink);
  font-size: 15px;
  line-height: 1.7;
}
.imgfield {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.shot {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: repeating-conic-gradient(var(--panel-2) 0% 25%, var(--panel) 0% 50%) 0 0 / 14px 14px;
  padding: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.shot img {
  max-height: 60px;
  max-width: 100%;
  object-fit: contain;
}
.shot.letterhead img {
  max-height: 90px;
  width: 100%;
}
.btns {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.pairs {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
@media (max-width: 620px) {
  .pairs {
    grid-template-columns: 1fr;
  }
}
.pair {
  display: flex;
  flex-direction: column;
  gap: 7px;
}
.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.sw {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  border: 1px solid color-mix(in srgb, var(--ink) 12%, transparent);
  cursor: pointer;
  padding: 0;
}
.sw.on {
  box-shadow: 0 0 0 2px var(--panel), 0 0 0 4px var(--blue);
}
.hexlabel {
  font-size: 11.5px;
  color: var(--ink-2);
}

.rprev {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: #ffffff;
  color: #0c1322;
  padding: 14px 16px 10px;
}
.rprev .lh {
  max-width: 100%;
  max-height: 64px;
  height: auto;
  display: block;
  margin: 0 auto 10px;
}
.rprev .rh {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 9px;
  border-bottom: 2px solid var(--accent);
}
.rprev .lg {
  height: 26px;
  max-width: 96px;
  object-fit: contain;
  flex: none;
}
.rprev .who {
  min-width: 0;
  flex: 1;
}
.rprev .ti {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.01em;
}
.rprev .su,
.rprev .me {
  font-size: 10px;
  color: #687386;
}
.rprev .me {
  text-align: end;
  flex: none;
}
.rprev .me b {
  display: block;
  color: #3a4456;
  font-size: 11px;
}
.rprev .series {
  display: flex;
  gap: 5px;
  margin: 12px 0;
}
.rprev .series i {
  height: 8px;
  flex: 1;
  border-radius: 3px;
  display: block;
}
.rprev .ft {
  border-top: 1px solid #eef1f6;
  padding-top: 7px;
  font-size: 9.5px;
  color: #98a1b2;
  display: flex;
  align-items: baseline;
  gap: 10px;
}
.rprev .ft .own {
  flex: 1;
  text-align: center;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.rprev .ft .pg {
  margin-inline-start: auto;
}

.savebar {
  position: sticky;
  bottom: 0;
  margin-top: 18px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: color-mix(in srgb, var(--panel) 92%, transparent);
  backdrop-filter: saturate(160%) blur(10px);
  box-shadow: var(--shadow-md);
}
.note {
  font-size: 12px;
  color: var(--muted);
  font-weight: 600;
}
.note.ok {
  color: var(--success);
}
.err.inline {
  margin: 0;
  font-size: 12px;
}
</style>
