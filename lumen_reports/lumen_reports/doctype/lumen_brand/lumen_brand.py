# Copyright (c) 2026 Lumen Solutions. All rights reserved.
# SPDX-License-Identifier: LicenseRef-Lumen-Proprietary
# Proprietary and confidential. See license.txt. "Lumen Reports" is a trademark of Lumen Solutions.
import frappe
from frappe.model.document import Document


class LumenBrand(Document):
	def on_update(self):
		# every dashboard that follows the identity is drawn from this document,
		# so a change has to reach the next page load rather than the next restart
		frappe.clear_document_cache("Lumen Brand", "Lumen Brand")
