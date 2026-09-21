# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
"""Visual identity checks: the merge, the guards and the colour reading.

bench --site <site> execute lumen_reports.dev.test_brand.run
bench --site <site> execute lumen_reports.dev.test_brand.cleanup
"""

import json
import os
from unittest.mock import patch

import frappe

from lumen_reports import brand, report
from lumen_reports.dev.test_perms import _user

BUILDER = "brand.builder@test.local"  # a Lumen Builder: may not touch the identity
FILES = ("lumen_brand_pair.png", "lumen_brand_one.png", "lumen_brand_onwhite.png", "lumen_brand_band.png")
BOARD = "lumen-brand-test"


def _write(name, draw) -> str:
	from PIL import Image

	image = Image.new("RGBA", (80, 60), (0, 0, 0, 0))
	draw(image)
	path = frappe.get_site_path("public", "files", name)
	image.save(path)
	return f"/files/{name}"


def _two_colours(image):
	# a wide red field and a narrower navy one, on transparent paper
	for x in range(6, 54):
		for y in range(6, 54):
			image.putpixel((x, y), (193, 18, 31, 255))
	for x in range(56, 76):
		for y in range(6, 54):
			image.putpixel((x, y), (0, 48, 73, 255))


def _one_colour(image):
	for x in range(10, 70):
		for y in range(10, 50):
			image.putpixel((x, y), (16, 122, 91, 255))


def _on_white(image):
	for x in range(80):
		for y in range(60):
			image.putpixel((x, y), (255, 255, 255, 255))
	for x in range(20, 60):
		for y in range(15, 45):
			image.putpixel((x, y), (123, 44, 191, 255))


def _band(image):
	# a wide, short band, the shape a letterhead comes in
	for x in range(80):
		for y in range(22, 38):
			image.putpixel((x, y), (0, 48, 73, 255))


def _dashboard():
	"""A throwaway board with one static element, so print has something to draw."""
	if frappe.db.exists("Lumen Dashboard", BOARD):
		frappe.delete_doc("Lumen Dashboard", BOARD, force=True, ignore_permissions=True)
	doc = frappe.get_doc(
		{
			"doctype": "Lumen Dashboard",
			"dashboard_title": "Identity Check",
			"route_slug": BOARD,
			"widgets": [
				{
					"widget_id": "note",
					"widget_type": "Text",
					"title": "Note",
					"style_json": json.dumps({"text": "Printed for the identity check."}),
				}
			],
			"layout_json": json.dumps([{"widget_id": "note", "x": 0, "y": 0, "w": 12, "h": 3}]),
		}
	)
	doc.insert(ignore_permissions=True)
	return doc


def run():
	out = {}
	_user(BUILDER, ["Lumen Builder"])

	# ---- the merge: a dashboard's own theme wins field by field
	saved = brand._clean_theme({"preset": "sand", "brand": "#c1121f", "secondary": "#003049", "radius": 0})
	out["clean_keeps_zero_radius"] = saved["radius"] == 0
	out["clean_lowercases_hex"] = brand._clean_theme({"brand": "#C1121F"})["brand"] == "#c1121f"
	out["clean_drops_bad_preset"] = brand._clean_theme({"preset": "neon"})["preset"] == ""
	out["clean_drops_bad_hex"] = brand._clean_theme({"brand": "red"})["brand"] == ""
	out["clean_clamps_radius"] = brand._clean_theme({"radius": 999})["radius"] == brand.MAX_RADIUS
	out["clean_drops_unknown_keys"] = "evil" not in brand._clean_theme({"evil": "1"})

	doc = frappe.get_doc("Lumen Brand")
	doc.organization = "Lumen Test Co"
	doc.footer_text = "Lumen Test Co · Confidential"
	doc.theme_json = json.dumps(saved)
	doc.logo = _write(FILES[0], _two_colours)
	doc.save(ignore_permissions=True)
	frappe.clear_document_cache("Lumen Brand", "Lumen Brand")

	merged = brand.resolve_theme({"brand": "#1463ff", "font": ""})
	out["dashboard_colour_wins"] = merged["brand"] == "#1463ff"
	out["identity_shows_through"] = merged["preset"] == "sand" and merged["secondary"] == "#003049"
	out["empty_does_not_override"] = brand.resolve_theme({"preset": ""})["preset"] == "sand"
	out["zero_radius_overrides"] = brand.resolve_theme({"radius": 0})["radius"] == 0
	out["no_theme_is_the_identity"] = brand.resolve_theme({}) == brand.theme()

	# ---- the print palette carries both colours of the pair
	palette = report._palette(brand.resolve_theme({}))
	out["palette_leads_with_the_pair"] = palette[0] == "#c1121f" and palette[1] == "#003049"
	out["palette_keeps_the_rest"] = len(palette) == 8 and palette[2] not in ("#c1121f", "#003049")

	# ---- who the report says it is from
	name, logo = report._company()
	out["report_names_the_organization"] = name == "Lumen Test Co"
	out["report_uses_the_identity_logo"] = bool(logo) and logo.endswith(FILES[0])

	# ---- files: only this site's public files, and only real ones
	for bad in ("https://example.com/logo.png", "/files/../../private/files/x.png", "/private/files/x.png"):
		try:
			brand._clean_file(bad, "Logo")
			out[f"refuses {bad[:28]}"] = False
		except frappe.ValidationError:
			frappe.clear_last_message()
			out[f"refuses {bad[:28]}"] = True
	out["blank_file_is_allowed"] = brand._clean_file("", "Logo") == ""

	# ---- reading colours out of an identity, with no AI in the loop
	pair = brand.extract_colors(doc.logo, use_ai=0)
	out["reads_both_colours"] = pair["primary"] == "#c1121f" and pair["secondary"] == "#003049"
	out["nothing_derived_from_a_pair"] = pair["secondary_derived"] is False
	out["source_is_the_image"] = pair["source"] == "image"

	one = brand.extract_colors(_write(FILES[1], _one_colour), use_ai=0)
	out["reads_a_single_colour"] = one["primary"] == "#107a5b"
	out["derives_the_second"] = one["secondary_derived"] is True and one["secondary"] != one["primary"]

	white = brand.extract_colors(_write(FILES[2], _on_white), use_ai=0)
	out["white_paper_is_not_a_brand"] = white["primary"] == "#7b2cbf"
	out["light_art_suggests_a_light_preset"] = white["suggested_preset"] == "light"

	# ---- the printed document wears the identity
	if report.reports_supported():
		doc.letterhead = _write(FILES[3], _band)
		doc.save(ignore_permissions=True)
		frappe.clear_document_cache("Lumen Brand", "Lumen Brand")
		board = _dashboard()
		markup = report.render_html(board, {"header": 1, "summary": 0, "page_numbers": 1})
		out["print_shows_the_letterhead"] = f'class="lhead"><img src="file://' in markup and FILES[3] in markup
		out["print_shows_the_logo"] = FILES[0] in markup
		out["print_names_the_organization"] = "Lumen Test Co" in markup
		out["print_uses_the_footer_line"] = 'content: "Lumen Test Co · Confidential"' in markup
		out["print_underlines_in_the_brand_colour"] = "border-bottom: 2pt solid #c1121f" in markup
		# a board with its own colour still prints in it
		board.theme_json = json.dumps({"brand": "#1463ff"})
		out["a_board_keeps_its_own_colour"] = (
			"border-bottom: 2pt solid #1463ff" in report.render_html(board, {"header": 1})
		)
		out["pdf_renders"] = len(report.render_pdf(board, {"header": 1})) > 1000

	# ---- the page hands the identity over, so the first frame is already themed
	from lumen_reports.www import lumen as page

	context = frappe._dict()
	# a CSRF token needs a real request session, which bench execute has none of
	with patch.object(frappe.sessions, "get_csrf_token", return_value="test"):
		page.get_context(context)
	booted = context.boot.get("lumen_brand") or {}
	out["boot_carries_the_identity"] = booted.get("organization") == "Lumen Test Co"
	out["boot_carries_the_theme"] = booted.get("theme", {}).get("brand") == "#c1121f"
	out["boot_says_who_may_edit"] = booted.get("can_manage") is True
	out["boot_is_serialisable"] = bool(json.dumps(context.boot))

	# ---- only a manager may change the identity
	frappe.set_user(BUILDER)
	try:
		brand.save_identity({"organization": "Hijacked"})
		out["builder_cannot_save"] = False
	except frappe.PermissionError:
		frappe.clear_last_message()
		out["builder_cannot_save"] = True
	try:
		brand.extract_colors(doc.logo, use_ai=0)
		out["builder_cannot_extract"] = False
	except frappe.PermissionError:
		frappe.clear_last_message()
		out["builder_cannot_extract"] = True
	out["builder_still_reads_it"] = brand.get_identity()["organization"] == "Lumen Test Co"
	out["builder_is_told_they_cannot"] = brand.get_identity()["can_manage"] is False
	frappe.set_user("Administrator")

	out["all_ok"] = all(v for v in out.values() if isinstance(v, bool))
	print(json.dumps(out, indent=1, default=str))


def cleanup():
	frappe.set_user("Administrator")
	doc = frappe.get_doc("Lumen Brand")
	doc.organization = ""
	doc.footer_text = ""
	doc.logo = ""
	doc.letterhead = ""
	doc.theme_json = "{}"
	doc.save(ignore_permissions=True)
	frappe.clear_document_cache("Lumen Brand", "Lumen Brand")
	for name in FILES:
		path = frappe.get_site_path("public", "files", name)
		if os.path.isfile(path):
			os.remove(path)
	if frappe.db.exists("Lumen Dashboard", BOARD):
		frappe.delete_doc("Lumen Dashboard", BOARD, force=True, ignore_permissions=True)
	if frappe.db.exists("User", BUILDER):
		frappe.delete_doc("User", BUILDER, force=True, ignore_permissions=True)
	frappe.db.commit()  # nosemgrep: frappe-manual-commit -- dev cleanup run from bench execute
	print("cleaned")
