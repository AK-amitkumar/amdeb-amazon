# -*- coding: utf-8 -*-

import logging

from ...models_access import OdooProductAccess
from ...model_names.shared_names import SHARED_NAME_FIELD
from ...model_names.product_template import (
    PRODUCT_AMAZON_DESCRIPTION_FIELD,
    PRODUCT_PRODUCT_BRAND_FIELD,
    PRODUCT_AMAZON_DEPARTMENT_FIELD,
    PRODUCT_AMAZON_ITEM_TYPE_FIELD,

)
from ...model_names.product_attribute import (
    PRODUCT_ATTRIBUTE_COLOR_VALUE,
    PRODUCT_ATTRIBUTE_SIZE_VALUE,
)
from ..amazon_names import (
    AMAZON_TITLE_FIELD, AMAZON_ITEM_TYPE_FIELD,
    AMAZON_DEPARTMENT_FIELD, AMAZON_BULLET_POINT_FIELD,
    AMAZON_VARIATION_THEME, AMAZON_DESCRIPTION_FIELD,
    AMAZON_PARENTAGE_FIELD, AMAZON_BRAND_FIELD,
    AMAZON_PARENTAGE_PARENT_VALUE, AMAZON_PARENTAGE_CHILD_VALUE,
    AMAZON_COLOR_FIELD, AMAZON_SIZE_FIELD,
    AMAZON_SIZE_COLOR_VALUE,
)
from .base_transfomer import BaseTransformer

_logger = logging.getLogger(__name__)

# list of required amazon fields and their corresponding model fields
_required_fields = [
    (AMAZON_DESCRIPTION_FIELD, PRODUCT_AMAZON_DESCRIPTION_FIELD),
    (AMAZON_TITLE_FIELD, SHARED_NAME_FIELD),
    (AMAZON_BRAND_FIELD, PRODUCT_PRODUCT_BRAND_FIELD),
    (AMAZON_DEPARTMENT_FIELD, PRODUCT_AMAZON_DEPARTMENT_FIELD),
    (AMAZON_ITEM_TYPE_FIELD, PRODUCT_AMAZON_ITEM_TYPE_FIELD),
]


class CreateTransformer(BaseTransformer):
    def _convert_description(self, sync_value):

        for required_field in _required_fields:
            field_value = self._product[required_field[1]]
            self._check_string(sync_value, required_field[0], field_value)

        bullet_points = OdooProductAccess.get_bullet_points(self._product)
        if bullet_points:
            sync_value[AMAZON_BULLET_POINT_FIELD] = bullet_points

    def _convert_variation(self, sync_value):
        has_attribute = False
        attributes = OdooProductAccess.get_variant_attributes(self._product)
        for attr in attributes:
            if attr[0] == PRODUCT_ATTRIBUTE_COLOR_VALUE:
                sync_value[AMAZON_COLOR_FIELD] = attr[1]
                has_attribute = True
            if attr[0] == PRODUCT_ATTRIBUTE_SIZE_VALUE:
                sync_value[AMAZON_SIZE_FIELD] = attr[1]
                has_attribute = True

        if not has_attribute:
            _logger.warning("No variant attribute found in sync transform.")
            sync_value = None
        return sync_value

    def _get_variant_theme(self, sync_value):
        attr_names = OdooProductAccess.get_template_attribute_names(
            self._product
        )

        has_color = PRODUCT_ATTRIBUTE_COLOR_VALUE in attr_names
        has_size = PRODUCT_ATTRIBUTE_SIZE_VALUE in attr_names
        if has_color and has_size:
            sync_value[AMAZON_VARIATION_THEME] = AMAZON_SIZE_COLOR_VALUE
        elif has_color:
            sync_value[AMAZON_VARIATION_THEME] = AMAZON_COLOR_FIELD
        elif has_size:
            sync_value[AMAZON_VARIATION_THEME] = AMAZON_SIZE_FIELD
        else:
            _logger.warning("No variant attribute found for multi-variant "
                            "template. Skip sync transform.")
            sync_value = None

        return sync_value

    def _convert_sync(self, sync_op):
        sync_value = super(CreateTransformer, self)._convert_sync(sync_op)
        self._convert_description(sync_value)
        # only three creation possibilities 1) a non-partial variant
        # 2) a multi-variant template 3) a single-variant template
        if OdooProductAccess.is_product_variant(self._product):
            # this is an independent variant
            sync_value[AMAZON_PARENTAGE_FIELD] = AMAZON_PARENTAGE_CHILD_VALUE
            sync_value = self._convert_variation(sync_value)
        else:
            if AMAZON_DESCRIPTION_FIELD not in sync_value:
                self._raise_exception(AMAZON_DESCRIPTION_FIELD)

            if OdooProductAccess.is_multi_variant_template(self._product):
                sync_value[AMAZON_PARENTAGE_FIELD] = (
                    AMAZON_PARENTAGE_PARENT_VALUE)
                sync_value = self._get_variant_theme(sync_value)

        return sync_value
