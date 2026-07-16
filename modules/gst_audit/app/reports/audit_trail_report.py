def build_audit_trail_text(events):
    return "\n".join(
        f"{e.get('created_at')} | {e.get('actor')} | {e.get('action')} | {e.get('event_hash')}"
        for e in events
    ) + "\n"
