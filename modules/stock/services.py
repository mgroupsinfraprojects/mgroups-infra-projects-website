import os
import shutil
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from werkzeug.utils import secure_filename
from time_utils import now_ist, today_code, timestamp_code, parse_local_datetime
from flask import current_app, request, session
from sqlalchemy import func
from extensions import db
from models import (
    Material, Location, Supplier, StockBalance, MaterialMovement, MovementItem,
    ReceiveConfirmation, StockLedger, Attachment, AuditLog
)

TRANSFER_TYPES = {"STORE_TO_SITE", "SITE_TO_SITE", "SITE_TO_STORE_RETURN", "MISC"}
RECEIVABLE_TYPES = {"STORE_TO_SITE", "SITE_TO_SITE", "SITE_TO_STORE_RETURN"}
IMMEDIATE_IN_TYPES = {"PURCHASE_TO_STORE", "OPENING_STOCK"}
IMMEDIATE_OUT_TYPES = {"SITE_CONSUMPTION", "DAMAGE_MISSING"}
ALL_MOVEMENT_TYPES = [
    ("PURCHASE_TO_STORE", "Purchase Material"),
    ("STORE_TO_SITE", "Send Store to Site"),
    ("SITE_TO_SITE", "Shift Site to Site"),
    ("SITE_TO_STORE_RETURN", "Return Site to Store"),
    ("SITE_CONSUMPTION", "Use Material at Site"),
    ("DAMAGE_MISSING", "Damage / Missing"),
    ("STOCK_ADJUSTMENT", "Physical Stock Count"),
    ("OPENING_STOCK", "Opening Stock"),
    ("MISC", "Other / Miscellaneous"),
]
MOVEMENT_TYPE_LABELS = dict(ALL_MOVEMENT_TYPES)
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "pdf"}
LOCATION_TYPE_PREFIX = {
    "Store": "STORE",
    "Site": "SITE",
    "Temporary Yard": "YARD",
    "Vehicle / In Transit": "VEHICLE",
    "Office": "OFFICE",
    "Other": "LOC",
}


def money(value):
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def get_current_user():
    """Login hook. No login page is included. Your external login can set session or headers."""
    return {
        "id": session.get("user_id") or request.headers.get("X-User-ID", "0"),
        "name": session.get("user_name") or request.headers.get("X-User-Name", "Admin"),
        "role": session.get("user_role") or request.headers.get("X-User-Role", "Admin"),
    }


def next_code(prefix, model, field_name):
    count = db.session.query(func.count(model.id)).scalar() or 0
    return f"{prefix}-{count + 1:05d}"


def next_movement_no():
    today = today_code()
    count = MaterialMovement.query.filter(MaterialMovement.movement_no.like(f"MOV-{today}-%")).count()
    return f"MOV-{today}-{count + 1:04d}"


def next_ledger_no():
    today = today_code()
    count = StockLedger.query.filter(StockLedger.ledger_no.like(f"LED-{today}-%")).count()
    return f"LED-{today}-{count + 1:05d}"


def normalize_float(value, default=0):
    try:
        if value in (None, ""):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def normalize_custom(select_value, custom_value):
    select_value = (select_value or "").strip()
    custom_value = (custom_value or "").strip()
    if select_value == "Other":
        return custom_value or "Other"
    return select_value or custom_value


def get_stock(location_id, material_id):
    stock = StockBalance.query.filter_by(location_id=location_id, material_id=material_id).first()
    return stock.quantity if stock else 0


def ensure_stock(location_id, material_id):
    stock = StockBalance.query.filter_by(location_id=location_id, material_id=material_id).first()
    if not stock:
        stock = StockBalance(location_id=location_id, material_id=material_id, quantity=0)
        db.session.add(stock)
        db.session.flush()
    return stock


def adjust_stock(location_id, material_id, delta, movement_type, direction, movement_id=None, reference_no="", remarks="", created_by="Admin", allow_negative=False):
    stock = ensure_stock(location_id, material_id)
    new_qty = (stock.quantity or 0) + delta
    if new_qty < -0.00001 and not allow_negative:
        mat = db.session.get(Material, material_id)
        loc = db.session.get(Location, location_id)
        raise ValueError(f"Insufficient stock for {mat.name if mat else material_id} at {loc.name if loc else location_id}. Available: {stock.quantity or 0:g}")
    stock.quantity = 0 if abs(new_qty) < 0.00001 else new_qty
    db.session.flush()
    ledger = StockLedger(
        ledger_no=next_ledger_no(),
        movement_id=movement_id,
        material_id=material_id,
        location_id=location_id,
        direction=direction,
        quantity=delta,
        balance_after=stock.quantity,
        movement_type=movement_type,
        reference_no=reference_no,
        remarks=remarks,
        created_by=created_by,
    )
    db.session.add(ledger)
    return stock


def audit(action, module, record_id="", description="", old_value="", new_value=""):
    user = get_current_user()
    log = AuditLog(
        user_id=str(user["id"]),
        user_name=user["name"],
        user_role=user["role"],
        action=action,
        module=module,
        record_id=str(record_id or ""),
        description=description,
        old_value=old_value,
        new_value=new_value,
        ip_address=request.remote_addr or "",
    )
    db.session.add(log)
    return log


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def save_upload(file_obj, subfolder, prefix="file"):
    if not file_obj or not getattr(file_obj, "filename", ""):
        return ""
    if not allowed_file(file_obj.filename):
        raise ValueError("Only png, jpg, jpeg, webp and pdf files are allowed.")
    safe = secure_filename(file_obj.filename)
    stamp = now_ist().strftime("%Y%m%d_%H%M%S_%f")
    filename = f"{secure_filename(prefix)}_{stamp}_{safe}"
    base = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
    os.makedirs(base, exist_ok=True)
    absolute = os.path.join(base, filename)
    file_obj.save(absolute)
    return f"uploads/{subfolder}/{filename}"


def attach_file(related_type, related_id, file_path, file_type="Photo"):
    if not file_path:
        return None
    user = get_current_user()
    att = Attachment(
        related_type=related_type,
        related_id=related_id,
        file_path=file_path,
        file_type=file_type,
        uploaded_by=user["name"],
    )
    db.session.add(att)
    return att


def movement_label(code):
    return MOVEMENT_TYPE_LABELS.get(code, code)


def parse_datetime(value):
    if not value:
        return now_ist()
    try:
        return parse_local_datetime(value)
    except ValueError:
        try:
            return parse_local_datetime(value)
        except ValueError:
            return now_ist()


def _movement_requirements(movement_type, stock_effect):
    if movement_type == "MISC":
        if stock_effect == "INCREASE":
            return False, True, "Closed"
        if stock_effect == "DECREASE":
            return True, False, "Closed"
        if stock_effect == "TRANSFER":
            return True, True, "In Transit"
        if stock_effect == "NO_EFFECT":
            return False, False, "Closed"
        raise ValueError("Stock effect is required for Other / Miscellaneous movement.")
    if movement_type in {"STORE_TO_SITE", "SITE_TO_SITE", "SITE_TO_STORE_RETURN"}:
        return True, True, "In Transit"
    if movement_type in {"SITE_CONSUMPTION", "DAMAGE_MISSING", "STOCK_ADJUSTMENT"}:
        return True, False, "Closed"
    if movement_type in {"PURCHASE_TO_STORE", "OPENING_STOCK"}:
        return False, True, "Closed"
    raise ValueError("Invalid movement type.")


def create_movement_from_form(form, files):
    user = get_current_user()
    movement_type = form.get("movement_type")
    if movement_type not in MOVEMENT_TYPE_LABELS:
        raise ValueError("Invalid movement type.")

    custom_movement_name = (form.get("custom_movement_name") or "").strip()
    stock_effect = form.get("stock_effect", "")
    needs_from, needs_to, status = _movement_requirements(movement_type, stock_effect)

    from_location_id = form.get("from_location_id") or None
    to_location_id = form.get("to_location_id") or None
    supplier_id = form.get("supplier_id") or None

    if needs_from and not from_location_id:
        raise ValueError("From location is required for this movement.")
    if needs_to and not to_location_id:
        raise ValueError("To location is required for this movement.")
    if needs_from and needs_to and from_location_id == to_location_id:
        raise ValueError("From and To location cannot be the same.")
    if movement_type == "MISC" and not custom_movement_name:
        raise ValueError("Custom movement name is required for Other / Miscellaneous.")

    movement = MaterialMovement(
        movement_no=next_movement_no(),
        movement_type=movement_type,
        custom_movement_name=custom_movement_name,
        stock_effect=stock_effect,
        from_location_id=int(from_location_id) if from_location_id else None,
        to_location_id=int(to_location_id) if to_location_id else None,
        supplier_id=int(supplier_id) if supplier_id else None,
        invoice_no=form.get("invoice_no", ""),
        dc_no=form.get("dc_no", ""),
        vehicle_no=form.get("vehicle_no", ""),
        driver_name=form.get("driver_name", ""),
        status=status,
        entered_by_id=str(user["id"]),
        entered_by=user["name"],
        entered_role=user["role"],
        movement_datetime=parse_datetime(form.get("movement_datetime")),
        remarks=form.get("remarks", ""),
    )
    db.session.add(movement)
    db.session.flush()

    material_ids = form.getlist("material_id[]")
    quantities = form.getlist("quantity[]")
    rates = form.getlist("rate[]")
    usage_types = form.getlist("usage_type[]")
    custom_usage_types = form.getlist("custom_usage_type[]")
    work_activities = form.getlist("work_activity[]")
    item_remarks = form.getlist("item_remarks[]")
    physical_quantities = form.getlist("physical_quantity[]")

    if not material_ids:
        raise ValueError("At least one material item is required.")

    any_item = False
    for idx, mid_raw in enumerate(material_ids):
        if not mid_raw:
            continue
        material_id = int(mid_raw)
        material = db.session.get(Material, material_id)
        if not material:
            raise ValueError("Material not found.")
        qty = normalize_float(quantities[idx] if idx < len(quantities) else 0)
        rate = normalize_float(rates[idx] if idx < len(rates) else material.standard_rate)
        usage_type = normalize_custom(usage_types[idx] if idx < len(usage_types) else "", custom_usage_types[idx] if idx < len(custom_usage_types) else "")
        work_activity = work_activities[idx] if idx < len(work_activities) else ""
        remarks = item_remarks[idx] if idx < len(item_remarks) else ""
        physical_qty = normalize_float(physical_quantities[idx] if idx < len(physical_quantities) else None, None)

        if movement_type != "STOCK_ADJUSTMENT" and stock_effect != "NO_EFFECT" and qty <= 0:
            continue
        any_item = True
        item = MovementItem(
            movement_id=movement.id,
            material_id=material_id,
            quantity_sent=qty,
            quantity_received=qty if (movement_type in IMMEDIATE_IN_TYPES or (movement_type == "MISC" and stock_effect == "INCREASE")) else 0,
            unit=material.unit,
            rate=rate,
            value=money(qty * rate),
            usage_type=usage_type,
            work_activity=work_activity,
            remarks=remarks,
        )

        if movement_type == "STOCK_ADJUSTMENT":
            if physical_qty is None:
                raise ValueError("Physical quantity is required for stock adjustment.")
            loc_id = int(from_location_id)
            system_qty = get_stock(loc_id, material_id)
            diff = physical_qty - system_qty
            item.quantity_sent = abs(diff)
            item.physical_quantity = physical_qty
            item.system_quantity = system_qty
            item.adjustment_diff = diff
            db.session.add(item)
            db.session.flush()
            if abs(diff) > 0.00001:
                adjust_stock(loc_id, material_id, diff, movement_type, "ADJUST", movement.id, movement.movement_no, f"Physical count adjustment: {remarks}", user["name"])
        elif movement_type in IMMEDIATE_IN_TYPES or (movement_type == "MISC" and stock_effect == "INCREASE"):
            db.session.add(item)
            db.session.flush()
            adjust_stock(int(to_location_id), material_id, qty, movement_type, "IN", movement.id, movement.movement_no, remarks or custom_movement_name or movement_label(movement_type), user["name"])
        elif movement_type in RECEIVABLE_TYPES or (movement_type == "MISC" and stock_effect == "TRANSFER"):
            db.session.add(item)
            db.session.flush()
            adjust_stock(int(from_location_id), material_id, -qty, movement_type, "OUT", movement.id, movement.movement_no, f"Dispatched to {movement.to_location.name if movement.to_location else 'destination'}", user["name"])
        elif movement_type in {"SITE_CONSUMPTION", "DAMAGE_MISSING"} or (movement_type == "MISC" and stock_effect == "DECREASE"):
            if movement_type == "DAMAGE_MISSING":
                item.damaged_quantity = qty
                item.usage_type = usage_type or "Damage / Missing"
            db.session.add(item)
            db.session.flush()
            adjust_stock(int(from_location_id), material_id, -qty, movement_type, "OUT", movement.id, movement.movement_no, usage_type or custom_movement_name or "Stock out", user["name"])
        elif movement_type == "MISC" and stock_effect == "NO_EFFECT":
            db.session.add(item)
            db.session.flush()

    if not any_item:
        raise ValueError("At least one valid quantity/material row is required.")

    invoice_path = save_upload(files.get("invoice_file"), "invoices", movement.movement_no) if files else ""
    proof_path = save_upload(files.get("proof_file"), "movements", movement.movement_no) if files else ""
    damage_path = save_upload(files.get("damage_file"), "damage", movement.movement_no) if files else ""
    attach_file("Movement", movement.id, invoice_path, "Invoice")
    attach_file("Movement", movement.id, proof_path, "Movement Proof")
    attach_file("Movement", movement.id, damage_path, "Damage / Missing Proof")

    audit("CREATE", "Material Movement", movement.id, f"Created {custom_movement_name or movement_label(movement_type)} {movement.movement_no}")
    return movement


def receive_movement_from_form(movement_id, form, files):
    user = get_current_user()
    movement = db.session.get(MaterialMovement, movement_id)
    if not movement:
        raise ValueError("Movement not found.")
    receivable = movement.movement_type in RECEIVABLE_TYPES or (movement.movement_type == "MISC" and movement.stock_effect == "TRANSFER")
    if not receivable:
        raise ValueError("Only transfer movements require receive confirmation.")
    if movement.status not in {"In Transit", "Partially Received", "Damaged"}:
        raise ValueError(f"Movement already closed or not receivable. Current status: {movement.status}")

    received_location_id = movement.to_location_id
    proof_path = save_upload(files.get("receive_proof_file"), "receipts", movement.movement_no) if files else ""
    confirmation = ReceiveConfirmation(
        movement_id=movement.id,
        received_by_id=str(user["id"]),
        received_by=user["name"],
        received_role=user["role"],
        received_datetime=parse_datetime(form.get("received_datetime")),
        received_location_id=received_location_id,
        proof_photo=proof_path,
        remarks=form.get("receive_remarks", ""),
    )
    db.session.add(confirmation)
    db.session.flush()
    attach_file("Receive", confirmation.id, proof_path, "Receive Proof")

    received_qtys = form.getlist("received_qty[]")
    damaged_qtys = form.getlist("damaged_qty[]")

    has_shortage = False
    has_damage = False
    full_received = True
    for idx, item in enumerate(movement.items):
        already_received = item.quantity_received or 0
        received = normalize_float(received_qtys[idx] if idx < len(received_qtys) else 0)
        damaged = normalize_float(damaged_qtys[idx] if idx < len(damaged_qtys) else 0)
        if received < 0 or damaged < 0:
            raise ValueError("Received/damaged quantity cannot be negative.")
        if already_received + received + damaged > item.quantity_sent + 0.00001:
            raise ValueError(f"Total received + damaged cannot exceed sent quantity for {item.material.name}.")
        item.quantity_received = already_received + received
        item.damaged_quantity = (item.damaged_quantity or 0) + damaged
        item.shortage_quantity = max(0, item.quantity_sent - item.quantity_received - item.damaged_quantity)
        if item.damaged_quantity > 0:
            has_damage = True
        if item.shortage_quantity > 0:
            has_shortage = True
        if abs(item.quantity_sent - item.quantity_received) > 0.00001 or item.damaged_quantity > 0 or item.shortage_quantity > 0:
            full_received = False
        if received > 0:
            adjust_stock(received_location_id, item.material_id, received, movement.movement_type, "IN", movement.id, movement.movement_no, "Received confirmation", user["name"])

    if has_damage:
        movement.status = "Damaged"
        confirmation.status = "Damaged"
    elif has_shortage or not full_received:
        movement.status = "Partially Received"
        confirmation.status = "Partially Received"
    else:
        movement.status = "Received"
        confirmation.status = "Received"

    audit("RECEIVE", "Receive Material", movement.id, f"Received {movement.movement_no} with status {movement.status}")
    return confirmation


def get_sqlite_db_path():
    db_uri = current_app.config["SQLALCHEMY_DATABASE_URI"]
    if not db_uri.startswith("sqlite:///"):
        raise ValueError("Built-in file backup supports SQLite only.")
    return db_uri.replace("sqlite:///", "", 1)


def create_backup():
    os.makedirs(current_app.config["BACKUP_FOLDER"], exist_ok=True)
    db_path = get_sqlite_db_path()
    if not os.path.exists(db_path):
        raise ValueError("Database file was not found.")
    filename = "inventory_backup_" + timestamp_code() + ".db"
    dest = os.path.join(current_app.config["BACKUP_FOLDER"], filename)
    shutil.copy2(db_path, dest)
    audit("BACKUP", "Backup", filename, "Created SQLite backup")
    return filename


def restore_backup(filename):
    if not filename or os.path.basename(filename) != filename or not filename.endswith(".db"):
        raise ValueError("Invalid backup file.")
    src = os.path.join(current_app.config["BACKUP_FOLDER"], filename)
    if not os.path.exists(src):
        raise ValueError("Backup file not found.")
    db_path = get_sqlite_db_path()
    safety = create_backup()
    # Commit safety-backup audit before replacing the SQLite file, then release file handles.
    db.session.commit()
    db.session.remove()
    db.engine.dispose()
    shutil.copy2(src, db_path)
    return safety


def list_backups():
    os.makedirs(current_app.config["BACKUP_FOLDER"], exist_ok=True)
    files = [f for f in os.listdir(current_app.config["BACKUP_FOLDER"]) if f.endswith(".db")]
    return sorted(files, reverse=True)


def location_has_stock_or_pending(location_id):
    stock_total = db.session.query(func.sum(StockBalance.quantity)).filter(StockBalance.location_id == location_id).scalar() or 0
    pending = MaterialMovement.query.filter(
        MaterialMovement.status.in_(["In Transit", "Partially Received", "Damaged"]),
        ((MaterialMovement.from_location_id == location_id) | (MaterialMovement.to_location_id == location_id))
    ).count()
    return stock_total, pending


def seed_defaults():
    if not Location.query.first():
        store = Location(location_code="STORE-00001", name="Central Store / Godown", type="Store", address="Main office godown")
        site = Location(location_code="SITE-00001", name="Sample Site", type="Site", address="Demo site")
        db.session.add_all([store, site])
    if not Material.query.first():
        db.session.add_all([
            Material(material_code="MAT-00001", name="Cement", category="Civil", brand="", size_spec="50kg", unit="Bag", min_stock=50, standard_rate=420),
            Material(material_code="MAT-00002", name="Steel TMT", category="Steel", size_spec="12mm", unit="Kg", min_stock=500, standard_rate=65),
            Material(material_code="MAT-00003", name="DI Pipe", category="Pipeline", size_spec="150mm", unit="Meter", min_stock=30, standard_rate=1200),
        ])
    if not Supplier.query.first():
        db.session.add(Supplier(supplier_code="SUP-00001", name="Default Supplier", contact_person="", phone=""))
    db.session.commit()
