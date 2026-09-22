# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""The site's visual identity: one saved look that dashboards and reports follow.

A dashboard's own theme still wins, field by field. Anything it leaves unset
falls through to here, and nothing is ever copied into a dashboard, so changing
the identity restyles every board that never overrode that field. An identity
nobody has set is empty, which is exactly what the app looked like before.

The identity also carries what a printed report needs to look like the
organization's own document: a name, a logo, an optional letterhead band and the
line at the foot of the page.
"""

import base64
import colorsys
import io
import json
import os
import re

import frappe
from frappe import _

# the theme keys a dashboard and the identity share. A dashboard theme is the
# same shape, so one merge covers both.
THEME_KEYS = ("preset", "brand", "secondary", "card", "radius", "density", "font", "surface")

PRESETS = ("light", "dark", "emerald", "midnight", "sand", "paper")
CARD_STYLES = ("flat", "outlined", "elevated", "glass")
DENSITIES = ("compact", "comfort")
SURFACES = ("solid", "gradient", "tint")
FONTS = ("", "system", "serif", "mono")

# The printed report's two faces. Kept here, not in the dashboard theme, because a theme is
# per dashboard while a report's typography is the organization's own.
REPORT_FONTS = ("Plus Jakarta Sans", "Inter")
REPORT_FONTS_AR = ("IBM Plex Sans Arabic", "Cairo", "Tajawal", "Almarai", "Noto Naskh Arabic")

MAX_RADIUS = 28
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")

# Pillow reads these; an SVG or a PDF is not an image to it, and guessing would
# print a broken picture on someone's report
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")

EMPTY_THEME = dict.fromkeys(THEME_KEYS, "")
EMPTY_THEME["radius"] = None


def _blank(value) -> bool:
	"""Empty means "not set here", so it falls through to the layer below.

	A radius of 0 is a real choice, which is why this is not a truth test."""
	return value is None or value == ""


# ---------------------------------------------------------------- reading


def _doc():
	"""The identity document, or None on a bench that has not migrated yet."""
	try:
		if not frappe.db.exists("DocType", "Lumen Brand"):
			return None
		return frappe.get_cached_doc("Lumen Brand")
	except Exception:
		return None


def get_brand() -> dict:
	"""The saved identity. Never raises: a report must print without one."""
	doc = _doc()
	if not doc:
		return {"organization": "", "logo": "", "letterhead": "", "footer_text": "",
			"report_font": REPORT_FONTS[0], "report_font_ar": REPORT_FONTS_AR[0],
			"theme": dict(EMPTY_THEME)}
	return {
		"organization": str(doc.organization or ""),
		"logo": str(doc.logo or ""),
		"letterhead": str(doc.letterhead or ""),
		"footer_text": str(doc.footer_text or ""),
		"report_font": _font(doc.get("report_font"), REPORT_FONTS),
		"report_font_ar": _font(doc.get("report_font_ar"), REPORT_FONTS_AR),
		"theme": _clean_theme(frappe.parse_json(doc.theme_json or "{}") or {}),
	}


def theme() -> dict:
	return get_brand()["theme"]


def resolve_theme(dashboard_theme) -> dict:
	"""A dashboard's theme over the identity, field by field."""
	out = dict(theme())
	for key, value in (dashboard_theme or {}).items():
		if not _blank(value):
			out[key] = value
	return out


def has_identity() -> bool:
	brand = get_brand()
	return bool(
		brand["organization"]
		or brand["logo"]
		or brand["letterhead"]
		or brand["footer_text"]
		or any(not _blank(v) for v in brand["theme"].values())
	)


# ---------------------------------------------------------------- validation


def _font(value, allowed) -> str:
	"""A font name is written into a stylesheet, so only a bundled one is ever let through."""
	value = str(value or "").strip()
	return value if value in allowed else allowed[0]


def _clean_theme(raw) -> dict:
	"""Keep only the keys and values the app can actually draw."""
	raw = raw if isinstance(raw, dict) else {}
	out = dict(EMPTY_THEME)

	preset = str(raw.get("preset") or "")
	if preset in PRESETS:
		out["preset"] = preset

	for key in ("brand", "secondary"):
		value = str(raw.get(key) or "").strip()
		if HEX.match(value):
			out[key] = value.lower()

	card = str(raw.get("card") or "")
	if card in CARD_STYLES:
		out["card"] = card

	density = str(raw.get("density") or "")
	if density in DENSITIES:
		out["density"] = density

	surface = str(raw.get("surface") or "")
	if surface in SURFACES:
		out["surface"] = surface

	font = str(raw.get("font") or "")
	if font in FONTS:
		out["font"] = font

	radius = raw.get("radius")
	if not _blank(radius):
		try:
			out["radius"] = max(0, min(MAX_RADIUS, int(float(radius))))
		except (TypeError, ValueError):
			out["radius"] = None

	return out


def _clean_file(url, label) -> str:
	"""Only a file already uploaded to this site, and only a public one.

	Print fetches images off the disk and refuses anything outside the site's
	public files, so a private attachment would silently print nothing."""
	url = str(url or "").strip()
	if not url:
		return ""
	if not url.startswith("/files/") or ".." in url:
		frappe.throw(_("{0}: upload the image to this site instead of linking to it.").format(label))
	if not os.path.isfile(_site_path(url)):
		frappe.throw(_("{0}: that file is not on this site any more.").format(label))
	return url


def _site_path(url) -> str:
	root = os.path.realpath(frappe.get_site_path("public", "files"))
	path = os.path.realpath(frappe.get_site_path("public", url.lstrip("/")))
	if path != root and not path.startswith(root + os.sep):
		frappe.throw(_("That file is outside this site's public files."))
	return path


def can_manage() -> bool:
	if frappe.session.user == "Administrator":
		return True
	return bool({"System Manager", "Lumen Manager"} & set(frappe.get_roles()))


def _require_manager():
	if not can_manage():
		frappe.throw(
			_("Only a Lumen Manager can change the visual identity."),
			frappe.PermissionError,
		)


# ---------------------------------------------------------------- endpoints


@frappe.whitelist()
def get_identity() -> dict:
	"""The identity as the app needs it, plus whether this person may change it."""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please login"), frappe.PermissionError)
	return {**get_brand(), "can_manage": can_manage()}


@frappe.whitelist()
def save_identity(payload) -> dict:
	_require_manager()
	data = frappe.parse_json(payload) if isinstance(payload, str) else (payload or {})
	if not isinstance(data, dict):
		frappe.throw(_("Nothing to save."))

	doc = frappe.get_doc("Lumen Brand")
	doc.organization = str(data.get("organization") or "").strip()[:140]
	doc.footer_text = str(data.get("footer_text") or "").strip()[:120]
	doc.logo = _clean_file(data.get("logo"), _("Logo"))
	doc.letterhead = _clean_file(data.get("letterhead"), _("Letterhead"))
	doc.report_font = _font(data.get("report_font"), REPORT_FONTS)
	doc.report_font_ar = _font(data.get("report_font_ar"), REPORT_FONTS_AR)
	doc.theme_json = json.dumps(_clean_theme(data.get("theme")))
	doc.save()
	frappe.clear_document_cache("Lumen Brand", "Lumen Brand")
	return get_identity()


# ---------------------------------------------------------------- colors


def _hex(rgb) -> str:
	r, g, b = (max(0, min(255, int(round(c)))) for c in rgb)
	return f"#{r:02x}{g:02x}{b:02x}"


def _rgb(value):
	h = str(value).lstrip("#")
	return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _hsv(rgb):
	r, g, b = (c / 255.0 for c in rgb)
	return colorsys.rgb_to_hsv(r, g, b)


def _hue_gap(a, b) -> float:
	"""Distance between two hues in degrees, the short way round the wheel."""
	d = abs(a - b) * 360.0
	return min(d, 360.0 - d)


def _read_image(path):
	from PIL import Image

	image = Image.open(path)
	image.draft("RGB", (320, 320))  # a big JPEG decodes at a fraction of the cost
	image = image.convert("RGBA")
	image.thumbnail((180, 180))
	return image


def _candidates(image, limit=6) -> tuple:
	"""The colors an identity is actually made of, most telling first.

	Transparent pixels are skipped rather than flattened, so a logo drawn for a
	dark background does not come back as a page of white."""
	pixels = [p for p in image.getdata() if p[3] >= 128]
	if not pixels:
		return [], 0.5

	buckets = {}
	for r, g, b, _a in pixels:
		key = (r >> 4, g >> 4, b >> 4)
		slot = buckets.setdefault(key, [0, 0, 0, 0])
		slot[0] += r
		slot[1] += g
		slot[2] += b
		slot[3] += 1

	total = len(pixels)
	lightness = sum(0.299 * r + 0.587 * g + 0.114 * b for r, g, b, _a in pixels) / (total * 255.0)

	scored = []
	for r_sum, g_sum, b_sum, count in buckets.values():
		rgb = (r_sum / count, g_sum / count, b_sum / count)
		hue, sat, val = _hsv(rgb)
		share = count / total
		# the page behind the mark, not the mark: flat white and flat black carry
		# no brand and would come back as everybody's "primary colour"
		if sat < 0.12 and (val > 0.92 or val < 0.12):
			continue
		scored.append({"hex": _hex(rgb), "share": share, "hue": hue, "sat": sat, "val": val,
		               "score": share * (0.35 + sat)})

	scored.sort(key=lambda c: c["score"], reverse=True)

	picked = []
	for colour in scored:
		close = any(
			_hue_gap(colour["hue"], other["hue"]) < 18 and abs(colour["val"] - other["val"]) < 0.22
			for other in picked
		)
		if close:
			continue
		picked.append(colour)
		if len(picked) >= limit:
			break

	return picked, lightness


def _pick_pair(picked) -> tuple:
	"""Primary and secondary out of the candidates, with a stated reason."""
	if not picked:
		return "", "", False

	coloured = [c for c in picked if c["sat"] >= 0.15]
	primary = (coloured or picked)[0]

	rest = [c for c in picked if c["hex"] != primary["hex"]]
	apart = [c for c in rest if c["sat"] >= 0.15 and _hue_gap(c["hue"], primary["hue"]) >= 35]
	if apart:
		return primary["hex"], apart[0]["hex"], False
	if rest:
		return primary["hex"], rest[0]["hex"], False

	# a one-colour mark still needs a second series colour: the same colour a
	# third of the way round the wheel reads as a deliberate pair
	hue = (primary["hue"] + 0.42) % 1.0
	sat = max(0.35, min(0.85, primary["sat"]))
	val = max(0.42, min(0.88, primary["val"]))
	rgb = tuple(c * 255 for c in colorsys.hsv_to_rgb(hue, sat, val))
	return primary["hex"], _hex(rgb), True


def _ai_refine(image, colours, key, model):
	"""Let Gemini name the brand colours it can see. Advice, never the answer.

	Anything unreadable falls back to what the pixels already said, because the
	person confirms the result either way."""
	from lumen_reports import ai

	buffer = io.BytesIO()
	small = image.copy()
	small.thumbnail((384, 384))
	small.convert("RGB").save(buffer, format="JPEG", quality=82)
	encoded = base64.b64encode(buffer.getvalue()).decode("ascii")

	listed = ", ".join(f"{c['hex']} ({c['share'] * 100:.0f}% of the mark)" for c in colours) or "none found"
	prompt = (
		"This image is an organization's visual identity (a logo, a letterhead or a "
		"brand sheet). Pick the two colours a dashboard should use: the primary, "
		"which is the colour the organization is known by, and a secondary that sits "
		"beside it without clashing.\n"
		f"Colours measured in the image: {listed}.\n"
		"Prefer a measured colour. Only return a colour that is not in that list if "
		"the image clearly shows it and the measurement missed it. Never return a "
		"near white or near black as the primary: those are the paper, not the brand.\n"
		'Answer as JSON: {"primary": "#rrggbb", "secondary": "#rrggbb", '
		'"note": "one short sentence naming the two colours"}'
	)
	result = ai._generate(prompt, key, model, image={"mime_type": "image/jpeg", "data": encoded})
	if not isinstance(result, dict):
		return None

	primary = str(result.get("primary") or "").strip().lower()
	secondary = str(result.get("secondary") or "").strip().lower()
	if not HEX.match(primary) or not HEX.match(secondary):
		return None
	# a model that answers "white" has described the page, not the identity
	_h, sat, val = _hsv(_rgb(primary))
	if sat < 0.10 and (val > 0.90 or val < 0.10):
		return None
	return {"primary": primary, "secondary": secondary, "note": str(result.get("note") or "")[:200]}


@frappe.whitelist()
def extract_colors(file_url: str, use_ai: int | str | bool = 1) -> dict:
	"""Read an uploaded identity and propose colours. The person confirms them.

	Measuring the pixels always works and needs no key. A Gemini key, when the
	site has one, only refines which two of the measured colours lead."""
	_require_manager()
	path = _site_path(_clean_file(file_url, _("Identity")))
	if not path.lower().endswith(IMAGE_SUFFIXES):
		frappe.throw(_("Upload the identity as a PNG, JPG or WEBP image."))

	try:
		image = _read_image(path)
	except Exception:
		frappe.throw(_("That image could not be read. Try a PNG or JPG export of the identity."))

	picked, lightness = _candidates(image)
	if not picked:
		frappe.throw(_("No colour stood out in that image. Try the logo on its own, or pick the colours by hand."))

	primary, secondary, derived = _pick_pair(picked)
	source = "image"
	note = ""

	if str(use_ai) not in ("0", "False", "false", ""):
		from lumen_reports import ai

		key, model, origin = ai._resolve_key()
		if key and origin:
			try:
				refined = _ai_refine(image, picked, key, model)
			except Exception:
				# a busy or unconfigured Gemini must not cost the person the
				# colours the image already gave up
				frappe.clear_last_message()
				refined = None
			if refined:
				primary, secondary = refined["primary"], refined["secondary"]
				derived = False
				source = "ai"
				note = refined["note"]

	swatches = [c["hex"] for c in picked]
	for colour in (secondary, primary):
		if colour and colour not in swatches:
			swatches.insert(0, colour)

	return {
		"primary": primary,
		"secondary": secondary,
		"colors": swatches[:8],
		"source": source,  # "ai" when Gemini chose the pair, "image" when the pixels did
		"secondary_derived": derived,
		"suggested_preset": "dark" if lightness < 0.34 else "light",
		"note": note,
	}
