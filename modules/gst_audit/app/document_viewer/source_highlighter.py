def build_highlight_payload(evidence_link):
    return {"source_file": evidence_link.source_file, "sheet_name": evidence_link.sheet_name, "row_number": evidence_link.row_number, "field_name": evidence_link.field_name}
