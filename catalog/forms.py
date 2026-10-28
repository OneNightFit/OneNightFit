from django.forms import ModelForm, TextInput, Textarea, URLInput, ModelChoiceField, Select, DecimalField

from catalog.models import Product

from django.core.exceptions import ValidationError
from django.utils.html import strip_tags

class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "description",
            "price",
        ]

        labels = {
            "name": "Nama Pakaian",
            "category": "Kategori Pakaian",
            "description": "Deskripsi Pakaian",
            "price": "Harga Pakaian",
        }

        widgets = {
            "name": TextInput(
                attrs={
                    "placeholder": "Nama pakaian",
                    "maxlength": 100,
                }
            ),
            "description": Textarea(
                attrs={
                    "placeholder": "Deskripsi pakaian",
                }
            ),
            "category": TextInput(
                attrs={
                    "placeholder": "Shirt, Dress, Trouser,",
                }
            ),
            "price": TextInput(
                attrs={
                    "placeholder": "Tulis dengan angka tanpa spasi dan koma",
                }
            ),
        }