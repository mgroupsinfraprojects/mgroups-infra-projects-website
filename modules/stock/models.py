from extensions import db
from time_utils import now_ist


class Material(db.Model):
    __tablename__ = "stock_materials"
    id = db.Column(db.Integer, primary_key=True)
    material_code = db.Column(db.String(40), unique=True, index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    category = db.Column(db.String(100), default="")
    sub_category = db.Column(db.String(100), default="")
    brand = db.Column(db.String(100), default="")
    size_spec = db.Column(db.String(140), default="")
    unit = db.Column(db.String(30), nullable=False)
    hsn_code = db.Column(db.String(40), default="")
    gst_percent = db.Column(db.Float, default=0)
    min_stock = db.Column(db.Float, default=0)
    standard_rate = db.Column(db.Float, default=0)
    photo_path = db.Column(db.String(255), default="")
    description = db.Column(db.Text, default="")
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=now_ist)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)

    def display_name(self):
        spec = f" - {self.size_spec}" if self.size_spec else ""
        return f"{self.name}{spec} ({self.unit})"


class Location(db.Model):
    __tablename__ = "stock_locations"
    id = db.Column(db.Integer, primary_key=True)
    location_code = db.Column(db.String(40), unique=True, index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    type = db.Column(db.String(50), nullable=False)  # Store / Site / Yard / Vehicle / Office / Other
    address = db.Column(db.String(255), default="")
    supervisor_name = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=now_ist)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)


class Supplier(db.Model):
    __tablename__ = "stock_suppliers"
    id = db.Column(db.Integer, primary_key=True)
    supplier_code = db.Column(db.String(40), unique=True, index=True)
    name = db.Column(db.String(180), nullable=False, index=True)
    contact_person = db.Column(db.String(120), default="")
    phone = db.Column(db.String(40), default="")
    gst_no = db.Column(db.String(40), default="")
    address = db.Column(db.String(255), default="")
    status = db.Column(db.String(20), default="Active")
    created_at = db.Column(db.DateTime, default=now_ist)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)


class StockBalance(db.Model):
    __tablename__ = "stock_balances"
    id = db.Column(db.Integer, primary_key=True)
    material_id = db.Column(db.Integer, db.ForeignKey("stock_materials.id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("stock_locations.id"), nullable=False)
    quantity = db.Column(db.Float, default=0)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)

    material = db.relationship("Material")
    location = db.relationship("Location")

    __table_args__ = (db.UniqueConstraint("material_id", "location_id", name="uq_stock_material_location"),)


class MaterialMovement(db.Model):
    __tablename__ = "stock_material_movements"
    id = db.Column(db.Integer, primary_key=True)
    movement_no = db.Column(db.String(60), unique=True, index=True)
    movement_type = db.Column(db.String(40), nullable=False, index=True)
    custom_movement_name = db.Column(db.String(120), default="")
    stock_effect = db.Column(db.String(40), default="")  # INCREASE / DECREASE / TRANSFER / NO_EFFECT
    from_location_id = db.Column(db.Integer, db.ForeignKey("stock_locations.id"), nullable=True)
    to_location_id = db.Column(db.Integer, db.ForeignKey("stock_locations.id"), nullable=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey("stock_suppliers.id"), nullable=True)
    invoice_no = db.Column(db.String(80), default="")
    dc_no = db.Column(db.String(80), default="")
    vehicle_no = db.Column(db.String(60), default="")
    driver_name = db.Column(db.String(120), default="")
    status = db.Column(db.String(40), default="Draft", index=True)
    entered_by_id = db.Column(db.String(80), default="")
    entered_by = db.Column(db.String(120), default="Admin")
    entered_role = db.Column(db.String(80), default="Admin")
    movement_datetime = db.Column(db.DateTime, default=now_ist, index=True)
    remarks = db.Column(db.Text, default="")
    created_at = db.Column(db.DateTime, default=now_ist)
    updated_at = db.Column(db.DateTime, default=now_ist, onupdate=now_ist)

    from_location = db.relationship("Location", foreign_keys=[from_location_id])
    to_location = db.relationship("Location", foreign_keys=[to_location_id])
    supplier = db.relationship("Supplier")
    items = db.relationship("MovementItem", backref="movement", cascade="all, delete-orphan")
    attachments = db.relationship("Attachment", primaryjoin="and_(foreign(Attachment.related_id)==MaterialMovement.id, Attachment.related_type=='Movement')", viewonly=True)


class MovementItem(db.Model):
    __tablename__ = "stock_movement_items"
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey("stock_material_movements.id"), nullable=False)
    material_id = db.Column(db.Integer, db.ForeignKey("stock_materials.id"), nullable=False)
    quantity_sent = db.Column(db.Float, default=0)
    quantity_received = db.Column(db.Float, default=0)
    shortage_quantity = db.Column(db.Float, default=0)
    damaged_quantity = db.Column(db.Float, default=0)
    physical_quantity = db.Column(db.Float, nullable=True)
    system_quantity = db.Column(db.Float, nullable=True)
    adjustment_diff = db.Column(db.Float, default=0)
    unit = db.Column(db.String(30), default="")
    rate = db.Column(db.Float, default=0)
    value = db.Column(db.Float, default=0)
    usage_type = db.Column(db.String(40), default="")  # Used / Damaged / Wasted / Scrap
    work_activity = db.Column(db.String(200), default="")
    remarks = db.Column(db.Text, default="")

    material = db.relationship("Material")


class ReceiveConfirmation(db.Model):
    __tablename__ = "stock_receive_confirmations"
    id = db.Column(db.Integer, primary_key=True)
    movement_id = db.Column(db.Integer, db.ForeignKey("stock_material_movements.id"), nullable=False)
    received_by_id = db.Column(db.String(80), default="")
    received_by = db.Column(db.String(120), default="Admin")
    received_role = db.Column(db.String(80), default="Admin")
    received_datetime = db.Column(db.DateTime, default=now_ist)
    received_location_id = db.Column(db.Integer, db.ForeignKey("stock_locations.id"), nullable=False)
    proof_photo = db.Column(db.String(255), default="")
    remarks = db.Column(db.Text, default="")
    status = db.Column(db.String(40), default="Received")
    created_at = db.Column(db.DateTime, default=now_ist)

    movement = db.relationship("MaterialMovement")
    received_location = db.relationship("Location")


class StockLedger(db.Model):
    __tablename__ = "stock_ledger"
    id = db.Column(db.Integer, primary_key=True)
    ledger_no = db.Column(db.String(60), unique=True, index=True)
    movement_id = db.Column(db.Integer, db.ForeignKey("stock_material_movements.id"), nullable=True)
    material_id = db.Column(db.Integer, db.ForeignKey("stock_materials.id"), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey("stock_locations.id"), nullable=False)
    direction = db.Column(db.String(20), nullable=False)  # IN, OUT, ADJUST
    quantity = db.Column(db.Float, nullable=False)  # signed quantity
    balance_after = db.Column(db.Float, nullable=False)
    movement_type = db.Column(db.String(40), nullable=False)
    reference_no = db.Column(db.String(80), default="")
    remarks = db.Column(db.Text, default="")
    created_by = db.Column(db.String(120), default="Admin")
    created_at = db.Column(db.DateTime, default=now_ist, index=True)

    movement = db.relationship("MaterialMovement")
    material = db.relationship("Material")
    location = db.relationship("Location")


class Attachment(db.Model):
    __tablename__ = "stock_attachments"
    id = db.Column(db.Integer, primary_key=True)
    related_type = db.Column(db.String(40), nullable=False)  # Material / Movement / Receive / Damage
    related_id = db.Column(db.Integer, nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(40), default="Photo")
    uploaded_by = db.Column(db.String(120), default="Admin")
    uploaded_at = db.Column(db.DateTime, default=now_ist)


class AuditLog(db.Model):
    __tablename__ = "stock_audit_logs"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(80), default="")
    user_name = db.Column(db.String(120), default="Admin")
    user_role = db.Column(db.String(80), default="Admin")
    action = db.Column(db.String(40), nullable=False)
    module = db.Column(db.String(80), nullable=False)
    record_id = db.Column(db.String(80), default="")
    description = db.Column(db.Text, default="")
    old_value = db.Column(db.Text, default="")
    new_value = db.Column(db.Text, default="")
    ip_address = db.Column(db.String(80), default="")
    created_at = db.Column(db.DateTime, default=now_ist, index=True)
