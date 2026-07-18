import os

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    """Central app configuration. Override any of these with environment variables."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-in-production")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'instance', 'warehouse.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    BARCODE_DIR = os.path.join(basedir, "static", "barcodes")
    COMPANY_NAME = os.environ.get("COMPANY_NAME", "Whistle Warehouse")
    DEFAULT_REORDER_THRESHOLD = 10
