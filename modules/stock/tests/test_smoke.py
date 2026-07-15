import os
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app
from extensions import db
from models import Location, Material, MaterialMovement, StockBalance


def make_app():
    app = create_app()
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + path
    app.config['TESTING'] = True
    with app.app_context():
        db.drop_all()
        db.create_all()
        store = Location(location_code='STORE-T', name='Central Store', type='Store')
        site_a = Location(location_code='SITE-A', name='Site A', type='Site')
        site_b = Location(location_code='SITE-B', name='Site B', type='Site')
        cement = Material(material_code='MAT-CEM', name='Cement', unit='Bag', standard_rate=420)
        db.session.add_all([store, site_a, site_b, cement])
        db.session.commit()
    return app


def stock_qty(location_id, material_id):
    s = StockBalance.query.filter_by(location_id=location_id, material_id=material_id).first()
    return s.quantity if s else 0


def test_core_flow():
    app = make_app()
    c = app.test_client()
    with app.app_context():
        store = Location.query.filter_by(type='Store').first()
        site_a = Location.query.filter_by(name='Site A').first()
        cement = Material.query.first()
        r = c.post('/movement/create', data={
            'movement_type':'OPENING_STOCK',
            'to_location_id':str(store.id),
            'movement_datetime':'2026-07-14T10:00',
            'material_id[]':[str(cement.id)],
            'quantity[]':['100'],
            'rate[]':['420'],
            'physical_quantity[]':[''],
            'usage_type[]':[''],
            'work_activity[]':[''],
            'item_remarks[]':['opening']
        }, follow_redirects=True)
        assert r.status_code == 200
        assert stock_qty(store.id, cement.id) == 100

        r = c.post('/movement/create', data={
            'movement_type':'STORE_TO_SITE',
            'from_location_id':str(store.id),
            'to_location_id':str(site_a.id),
            'vehicle_no':'TN-74-1234',
            'movement_datetime':'2026-07-14T11:00',
            'material_id[]':[str(cement.id)],
            'quantity[]':['40'],
            'rate[]':['0'],
            'physical_quantity[]':[''],
            'usage_type[]':[''],
            'work_activity[]':[''],
            'item_remarks[]':['dispatch']
        }, follow_redirects=True)
        assert r.status_code == 200
        assert stock_qty(store.id, cement.id) == 60
        assert stock_qty(site_a.id, cement.id) == 0
        movement = MaterialMovement.query.filter_by(movement_type='STORE_TO_SITE').first()
        assert movement.status == 'In Transit'

        r = c.post(f'/receive/{movement.id}/submit', data={
            'received_datetime':'2026-07-14T12:00',
            'receive_remarks':'ok',
            'received_qty[]':['38'],
            'damaged_qty[]':['1']
        }, follow_redirects=True)
        assert r.status_code == 200
        assert stock_qty(site_a.id, cement.id) == 38
        assert movement.status in {'Damaged', 'Partially Received'}

        dashboard = c.get('/')
        assert dashboard.status_code == 200
        assert b'Material Location Dashboard' in dashboard.data
        assert b'Today Entries' in dashboard.data

        # SQLite does not preserve timezone metadata. The app intentionally stores
        # naive IST-local timestamps rather than using misleading timezone=True.
        db.session.refresh(movement)
        assert movement.created_at.tzinfo is None
        assert movement.movement_datetime.tzinfo is None
