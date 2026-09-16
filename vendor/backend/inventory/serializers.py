from rest_framework import serializers
from .selectors import get_vendor_stock_status


class VendorStockListSerializer(serializers.Serializer):
    """List row for GET /api/vendor/stock/ -- one Package + its live stock state."""
    product_id = serializers.IntegerField(source="id")
    name = serializers.CharField()
    slug = serializers.CharField()
    image = serializers.CharField(allow_blank=True, allow_null=True)

    def _status(self, obj):
        if not hasattr(obj, "_cached_vendor_status"):
            obj._cached_vendor_status = get_vendor_stock_status(obj)
        return obj._cached_vendor_status

    state = serializers.SerializerMethodField()
    today_available_grams = serializers.SerializerMethodField()
    today_available_display = serializers.SerializerMethodField()
    default_daily_grams = serializers.SerializerMethodField()
    default_daily_display = serializers.SerializerMethodField()
    opening_stock_grams = serializers.SerializerMethodField()
    opening_stock_display = serializers.SerializerMethodField()
    consumed_stock_grams = serializers.SerializerMethodField()
    consumed_stock_display = serializers.SerializerMethodField()
    restock_level_grams = serializers.SerializerMethodField()
    restock_level_display = serializers.SerializerMethodField()
    reorder_level_grams = serializers.SerializerMethodField()
    reorder_level_display = serializers.SerializerMethodField()
    price = serializers.SerializerMethodField()
    mrp = serializers.SerializerMethodField()
    offer_price = serializers.SerializerMethodField()
    offer_percentage = serializers.SerializerMethodField()
    vegetable_gram = serializers.SerializerMethodField()
    unit = serializers.SerializerMethodField()
    is_claimed = serializers.SerializerMethodField()
    is_mine = serializers.SerializerMethodField()

    def get_state(self, obj): return self._status(obj)["state"]
    def get_today_available_grams(self, obj): return self._status(obj)["today_available_grams"]
    def get_today_available_display(self, obj): return self._status(obj)["today_available_display"]
    def get_default_daily_grams(self, obj): return self._status(obj)["default_daily_grams"]
    def get_default_daily_display(self, obj): return self._status(obj)["default_daily_display"]
    def get_opening_stock_grams(self, obj): return self._status(obj)["opening_stock_grams"]
    def get_opening_stock_display(self, obj): return self._status(obj)["opening_stock_display"]
    def get_consumed_stock_grams(self, obj): return self._status(obj)["consumed_stock_grams"]
    def get_consumed_stock_display(self, obj): return self._status(obj)["consumed_stock_display"]
    def get_restock_level_grams(self, obj): return self._status(obj)["restock_level_grams"]
    def get_restock_level_display(self, obj): return self._status(obj)["restock_level_display"]
    def get_reorder_level_grams(self, obj): return self._status(obj)["reorder_level_grams"]
    def get_reorder_level_display(self, obj): return self._status(obj)["reorder_level_display"]
    def get_price(self, obj): return self._status(obj)["price"]
    def get_mrp(self, obj): return self._status(obj)["mrp"]
    def get_offer_price(self, obj): return self._status(obj)["offer_price"]
    def get_offer_percentage(self, obj): return self._status(obj)["offer_percentage"]
    def get_vegetable_gram(self, obj): return self._status(obj)["vegetable_gram"]
    def get_unit(self, obj): return self._status(obj)["unit"]
    def get_is_claimed(self, obj): return self._status(obj)["is_claimed"]

    def get_is_mine(self, obj):
        company = self.context.get("company")
        owning_id = self._status(obj)["owning_company_id"]
        if owning_id is None:
            return None  # unclaimed -- not yet anyone's
        return company is not None and owning_id == company.id


class RestockActionSerializer(serializers.Serializer):
    quantity = serializers.FloatField(required=True)
    unit = serializers.ChoiceField(choices=["g", "kg", "grams", "kilograms"], default="kg")


class AdjustActionSerializer(serializers.Serializer):
    quantity = serializers.FloatField(required=True)
    unit = serializers.ChoiceField(choices=["g", "kg", "grams", "kilograms"], default="kg")
    reason = serializers.CharField(required=True, allow_blank=False)


class UpdateDetailsSerializer(serializers.Serializer):
    price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    offer_price = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    reorder_level_quantity = serializers.FloatField(required=False, allow_null=True)
    reorder_level_unit = serializers.ChoiceField(choices=["g", "kg", "grams", "kilograms"], default="kg", required=False)
    restock_level_quantity = serializers.FloatField(required=False, allow_null=True)
    restock_level_unit = serializers.ChoiceField(choices=["g", "kg", "grams", "kilograms"], default="kg", required=False)
