import json
import logging
from datetime import datetime, UTC

from django.core.cache import cache

from .models import Cart, CartItem
from .kafka_producer import publish_cart_checkout

logger = logging.getLogger(__name__)

CART_CACHE_TTL = 3600


def _cache_key(user_id: str) -> str:
    return f'cart:user:{user_id}'


def _serialize_cart(cart: Cart) -> dict:
    data = cart.to_mongo().to_dict()
    data['_id'] = str(data.get('_id', ''))
    return data


def _store_in_cache(user_id: str, cart: Cart) -> None:
    try:
        cache.set(_cache_key(user_id), json.dumps(_serialize_cart(cart)), CART_CACHE_TTL)
    except Exception as exc:
        logger.warning("Redis cache write failed: %s", exc)


def _get_from_cache(user_id: str) -> dict | None:
    try:
        raw = cache.get(_cache_key(user_id))
        if raw:
            return json.loads(raw)
    except Exception as exc:
        logger.warning("Redis cache read failed: %s", exc)
    return None


def _invalidate_cache(user_id: str) -> None:
    try:
        cache.delete(_cache_key(user_id))
    except Exception as exc:
        logger.warning("Redis cache delete failed: %s", exc)


class CartService:
    def get_cart(self, user_id: str) -> Cart | None:
        return Cart.objects(user_id=user_id).first()

    def add_to_cart(self, user_id: str, product_data: dict, quantity: int) -> Cart:
        cart = self.get_cart(user_id)
        if not cart:
            cart = Cart(
                user_id=user_id,
                items=[],
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            cart.save()

        item_quantity = int(product_data.get('quantity', quantity))
        for item in cart.items:
            if item.product_id == str(product_data['product_id']):
                item.quantity += item_quantity
                item.total = item.price * item.quantity
                break
        else:
            cart_item = CartItem(
                product_id=str(product_data['product_id']),
                name=product_data.get('name', ''),
                price=float(product_data['price']),
                quantity=item_quantity,
                image_url=product_data.get('image_url', ''),
                total=float(product_data['price']) * item_quantity,
            )
            cart.items.append(cart_item)

        cart.updated_at = datetime.now(UTC)
        cart.save()
        _store_in_cache(user_id, cart)
        return cart

    def remove_from_cart(self, user_id: str, product_id: str) -> Cart | None:
        cart = self.get_cart(user_id)
        if not cart:
            return None
        cart.items = [item for item in cart.items if item.product_id != product_id]
        cart.updated_at = datetime.now(UTC)
        cart.save()
        _store_in_cache(user_id, cart)
        return cart

    def update_cart_item(self, user_id: str, product_id: str, quantity: int) -> Cart | None:
        cart = self.get_cart(user_id)
        if not cart:
            return None
        for item in cart.items:
            if item.product_id == product_id:
                item.quantity = quantity
                item.total = item.price * quantity
                break
        cart.updated_at = datetime.now(UTC)
        cart.save()
        _store_in_cache(user_id, cart)
        return cart

    def review_cart(self, user_id: str) -> dict | None:
        cached = _get_from_cache(user_id)
        if cached:
            cached['total'] = sum(item['total'] for item in cached.get('items', []))
            return cached

        cart = self.get_cart(user_id)
        if not cart:
            return None
        _store_in_cache(user_id, cart)
        cart_dict = _serialize_cart(cart)
        cart_dict['total'] = sum(item['total'] for item in cart_dict.get('items', []))
        return cart_dict

    def checkout_cart(self, user_id: str, address: str, payment_method: str) -> dict | None:
        cart = self.get_cart(user_id)
        if not cart:
            return None
        cart_dict = _serialize_cart(cart)
        cart_dict['total'] = sum(item['total'] for item in cart_dict.get('items', []))
        _invalidate_cache(user_id)
        publish_cart_checkout(user_id, cart_dict)
        return {
            'cart': cart_dict,
            'address': address,
            'payment_method': payment_method,
        }
