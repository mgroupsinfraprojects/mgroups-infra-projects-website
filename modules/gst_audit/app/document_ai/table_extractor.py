def normalize_table_rows(rows):
    return [list(map(str, row)) for row in rows if any(str(cell).strip() for cell in row)]
