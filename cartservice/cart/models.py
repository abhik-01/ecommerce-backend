import uuid
import mongoengine as me


class CartItem(me.EmbeddedDocument):
    product_id = me.StringField(required=True)
    name = me.StringField()
    price = me.FloatField(required=True)
    quantity = me.IntField(required=True, min_value=1)
    image_url = me.StringField()
    total = me.FloatField(required=True)


class Cart(me.Document):
    cart_id = me.UUIDField(binary=False, default=uuid.uuid4, unique=True, required=True)
    user_id = me.StringField(required=True, index=True)
    items = me.EmbeddedDocumentListField(CartItem)
    created_at = me.DateTimeField(required=True)
    updated_at = me.DateTimeField(required=True)

    meta = {
        'indexes': [
            'user_id',
            'cart_id',
        ]
    }
