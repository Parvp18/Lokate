# Import all models so they're registered with Base.metadata
from app.models.warehouse import Warehouse, Row, Bin  # noqa: F401
from app.models.vendor import Vendor, vendor_product  # noqa: F401
from app.models.product import Product  # noqa: F401
from app.models.inventory import InventoryItem  # noqa: F401
from app.models.movement import StockMovement, MovementType  # noqa: F401
from app.models.order import Order, OrderLineItem, OrderStatus  # noqa: F401
from app.models.delivery import Delivery, DeliveryTrackingEvent, DeliveryStatus  # noqa: F401
