from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Supplier(db.Model):
    """A vendor that products can be sourced from."""

    __tablename__ = "suppliers"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    contact_email = db.Column(db.String(120))
    phone = db.Column(db.String(40))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    products = db.relationship("Product", backref="supplier", lazy=True)

    def __repr__(self):
        return f"<Supplier {self.name}>"


class Product(db.Model):
    """A single SKU tracked in the warehouse, identified by its barcode."""

    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    sku = db.Column(db.String(40), unique=True, nullable=False, index=True)
    name = db.Column(db.String(150), nullable=False)
    category = db.Column(db.String(80), default="General", nullable=False)

    quantity = db.Column(db.Integer, default=0, nullable=False)
    unit_price = db.Column(db.Float, default=0.0, nullable=False)
    reorder_threshold = db.Column(db.Integer, default=10, nullable=False)

    aisle = db.Column(db.String(10), default="A", nullable=False)
    bin = db.Column(db.String(10), default="1", nullable=False)

    supplier_id = db.Column(db.Integer, db.ForeignKey("suppliers.id"), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    transactions = db.relationship(
        "Transaction", backref="product", lazy=True,
        order_by="Transaction.performed_at.desc()", cascade="all, delete-orphan",
    )

    @property
    def is_low_stock(self):
        return self.quantity <= self.reorder_threshold

    @property
    def is_out_of_stock(self):
        return self.quantity <= 0

    @property
    def total_value(self):
        return round(self.quantity * self.unit_price, 2)

    @property
    def location(self):
        return f"{self.aisle}-{self.bin}"

    @property
    def stock_ratio(self):
        """Quantity relative to reorder threshold, used to color the stock heatmap."""
        if self.reorder_threshold <= 0:
            return 2.0
        return self.quantity / self.reorder_threshold

    def to_dict(self):
        return {
            "id": self.id,
            "sku": self.sku,
            "name": self.name,
            "category": self.category,
            "quantity": self.quantity,
            "unit_price": self.unit_price,
            "total_value": self.total_value,
            "reorder_threshold": self.reorder_threshold,
            "is_low_stock": self.is_low_stock,
            "is_out_of_stock": self.is_out_of_stock,
            "location": self.location,
            "supplier": self.supplier.name if self.supplier else None,
        }

    def __repr__(self):
        return f"<Product {self.sku} ({self.name})>"


class Transaction(db.Model):
    """A single stock movement: a scan-in (receiving) or scan-out (pick/sale)."""

    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    type = db.Column(db.String(3), nullable=False)  # "IN" or "OUT"
    quantity = db.Column(db.Integer, nullable=False)
    note = db.Column(db.String(200))
    performed_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "product_id": self.product_id,
            "product_name": self.product.name,
            "sku": self.product.sku,
            "type": self.type,
            "quantity": self.quantity,
            "note": self.note,
            "performed_at": self.performed_at.strftime("%Y-%m-%d %H:%M:%S"),
        }

    def __repr__(self):
        return f"<Transaction {self.type} {self.quantity} of product #{self.product_id}>"
