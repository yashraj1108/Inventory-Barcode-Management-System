import os
from datetime import datetime, date, timedelta

from flask import Flask, render_template, request, redirect, url_for, jsonify, flash

from config import Config
from models import db, Product, Supplier, Transaction
from barcode_utils import generate_barcode, safe_filename


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    os.makedirs(os.path.join(app.root_path, "instance"), exist_ok=True)
    os.makedirs(app.config["BARCODE_DIR"], exist_ok=True)

    db.init_app(app)
    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


def apply_transaction(product, txn_type, quantity, note=None):
    """
    Shared stock-movement logic used by both the barcode scanner API and the
    plain HTML "adjust stock" form. Returns (ok: bool, message: str, txn or None).
    """
    if txn_type not in ("IN", "OUT"):
        return False, "Type must be IN or OUT.", None
    if quantity is None or quantity <= 0:
        return False, "Quantity must be greater than zero.", None
    if txn_type == "OUT" and quantity > product.quantity:
        return False, f"Only {product.quantity} units of {product.name} in stock.", None

    product.quantity += quantity if txn_type == "IN" else -quantity
    txn = Transaction(product_id=product.id, type=txn_type, quantity=quantity, note=note or None)
    db.session.add(txn)
    db.session.commit()

    verb = "Received" if txn_type == "IN" else "Removed"
    return True, f"{verb} {quantity} × {product.name}. New stock: {product.quantity}.", txn


def register_routes(app):

    # ---------- Pages ----------

    @app.route("/")
    def dashboard():
        products = Product.query.all()
        total_skus = len(products)
        total_value = round(sum(p.total_value for p in products), 2)
        low_stock = sorted([p for p in products if p.is_low_stock], key=lambda p: p.stock_ratio)
        recent_transactions = Transaction.query.order_by(Transaction.performed_at.desc()).limit(6).all()

        # Group products by warehouse location for the stock heatmap
        locations = {}
        for p in products:
            locations.setdefault(p.location, []).append(p)
        location_cells = []
        for loc, items in sorted(locations.items()):
            worst_ratio = min(i.stock_ratio for i in items)
            location_cells.append({"location": loc, "items": items, "ratio": worst_ratio})

        return render_template(
            "dashboard.html",
            company_name=app.config["COMPANY_NAME"],
            total_skus=total_skus,
            total_value=total_value,
            low_stock=low_stock,
            recent_transactions=recent_transactions,
            location_cells=location_cells,
        )

    @app.route("/products")
    def products():
        q = request.args.get("q", "").strip()
        query = Product.query
        if q:
            like = f"%{q}%"
            query = query.filter(
                db.or_(Product.name.ilike(like), Product.sku.ilike(like), Product.category.ilike(like))
            )
        all_products = query.order_by(Product.name).all()
        return render_template(
            "products.html", products=all_products, q=q, company_name=app.config["COMPANY_NAME"]
        )

    @app.route("/products/new", methods=["GET", "POST"])
    def product_new():
        suppliers = Supplier.query.order_by(Supplier.name).all()

        if request.method == "POST":
            sku = request.form.get("sku", "").strip().upper()
            name = request.form.get("name", "").strip()
            category = request.form.get("category", "General").strip() or "General"
            aisle = (request.form.get("aisle", "A").strip() or "A").upper()
            bin_ = request.form.get("bin", "1").strip() or "1"

            try:
                quantity = max(0, int(request.form.get("quantity", 0) or 0))
                unit_price = max(0.0, float(request.form.get("unit_price", 0) or 0))
                reorder_threshold = max(0, int(request.form.get("reorder_threshold", 10) or 10))
            except ValueError:
                flash("Quantity, price, and reorder threshold must be numbers.", "error")
                return redirect(url_for("product_new"))

            supplier_raw = request.form.get("supplier_id") or ""
            supplier_id = int(supplier_raw) if supplier_raw.isdigit() else None

            if not sku or not name:
                flash("SKU and product name are required.", "error")
                return redirect(url_for("product_new"))

            if Product.query.filter_by(sku=sku).first():
                flash(f"SKU '{sku}' already exists.", "error")
                return redirect(url_for("product_new"))

            product = Product(
                sku=sku, name=name, category=category, quantity=quantity,
                unit_price=unit_price, reorder_threshold=reorder_threshold,
                aisle=aisle, bin=bin_, supplier_id=supplier_id,
            )
            db.session.add(product)
            db.session.commit()

            generate_barcode(sku, app.config["BARCODE_DIR"])

            if quantity > 0:
                db.session.add(Transaction(product_id=product.id, type="IN", quantity=quantity, note="Initial stock"))
                db.session.commit()

            flash(f"{name} added and barcode generated.", "success")
            return redirect(url_for("product_detail", product_id=product.id))

        return render_template("product_new.html", suppliers=suppliers, company_name=app.config["COMPANY_NAME"])

    @app.route("/products/<int:product_id>")
    def product_detail(product_id):
        product = Product.query.get_or_404(product_id)
        barcode_filename = safe_filename(product.sku) + ".png"
        return render_template(
            "product_detail.html", product=product, barcode_filename=barcode_filename,
            company_name=app.config["COMPANY_NAME"],
        )

    @app.route("/products/<int:product_id>/adjust", methods=["POST"])
    def product_adjust(product_id):
        product = Product.query.get_or_404(product_id)
        txn_type = (request.form.get("type") or "").strip().upper()
        note = request.form.get("note", "").strip()
        try:
            quantity = int(request.form.get("quantity", 0) or 0)
        except ValueError:
            quantity = 0

        ok, message, _ = apply_transaction(product, txn_type, quantity, note)
        flash(message, "success" if ok else "error")
        return redirect(url_for("product_detail", product_id=product.id))

    @app.route("/scan")
    def scan():
        return render_template("scan.html", company_name=app.config["COMPANY_NAME"])

    @app.route("/history")
    def history():
        type_filter = request.args.get("type", "")
        query = Transaction.query
        if type_filter in ("IN", "OUT"):
            query = query.filter_by(type=type_filter)
        txns = query.order_by(Transaction.performed_at.desc()).limit(200).all()
        return render_template(
            "history.html", transactions=txns, type_filter=type_filter,
            company_name=app.config["COMPANY_NAME"],
        )

    @app.route("/suppliers", methods=["GET", "POST"])
    def suppliers():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            email = request.form.get("contact_email", "").strip()
            phone = request.form.get("phone", "").strip()
            if not name:
                flash("Supplier name is required.", "error")
            else:
                db.session.add(Supplier(name=name, contact_email=email, phone=phone))
                db.session.commit()
                flash(f"Supplier '{name}' added.", "success")
            return redirect(url_for("suppliers"))

        all_suppliers = Supplier.query.order_by(Supplier.name).all()
        return render_template(
            "suppliers.html", suppliers=all_suppliers, company_name=app.config["COMPANY_NAME"]
        )

    # ---------- JSON API (used by the barcode scanner) ----------

    @app.route("/api/lookup", methods=["POST"])
    def api_lookup():
        data = request.get_json(silent=True) or {}
        code = (data.get("barcode") or "").strip().upper()
        if not code:
            return jsonify({"status": "error", "message": "No barcode provided."}), 400

        product = Product.query.filter_by(sku=code).first()
        if not product:
            return jsonify({"status": "not_found", "message": f"No product matches '{code}'."}), 404

        return jsonify({"status": "found", "product": product.to_dict()})

    @app.route("/api/transaction", methods=["POST"])
    def api_transaction():
        data = request.get_json(silent=True) or {}
        code = (data.get("barcode") or "").strip().upper()
        txn_type = (data.get("type") or "").strip().upper()
        note = (data.get("note") or "").strip()
        try:
            quantity = int(data.get("quantity", 0))
        except (TypeError, ValueError):
            quantity = 0

        product = Product.query.filter_by(sku=code).first()
        if not product:
            return jsonify({"status": "not_found", "message": f"No product matches '{code}'."}), 404

        ok, message, txn = apply_transaction(product, txn_type, quantity, note)
        if not ok:
            return jsonify({"status": "error", "message": message, "product": product.to_dict()}), 400

        return jsonify({
            "status": "success",
            "message": message,
            "product": product.to_dict(),
            "transaction": txn.to_dict(),
        })

    @app.route("/api/stats")
    def api_stats():
        products = Product.query.all()
        total_value = round(sum(p.total_value for p in products), 2)
        low_stock = sum(1 for p in products if p.is_low_stock)

        today_start = datetime.combine(date.today(), datetime.min.time())
        today_end = today_start + timedelta(days=1)
        today_txns = Transaction.query.filter(
            Transaction.performed_at >= today_start, Transaction.performed_at < today_end
        ).count()

        return jsonify({
            "total_skus": len(products),
            "total_value": total_value,
            "low_stock": low_stock,
            "today_transactions": today_txns,
        })


app = create_app()

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5001)
