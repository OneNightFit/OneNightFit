from django.forms import ModelForm, TextInput, Textarea, URLInput, Select

from catalog.models import Product


class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "size",
            "description",
            "price",
            "image",
        ]

        labels = {
            "name": "Nama Pakaian",
            "category": "Kategori Pakaian",
            "size": "Ukuran",
            "description": "Deskripsi Pakaian",
            "price": "Harga Pakaian",
            "image": "URL Gambar",
        }

        widgets = {
            "name": TextInput(attrs={"placeholder": "Nama pakaian", "maxlength": 100}),
            "category": Select(),
            "size": Select(),
            "description": Textarea(attrs={"placeholder": "Deskripsi pakaian"}),
            "price": TextInput(attrs={"placeholder": "Tulis dengan angka tanpa spasi dan koma"}),
            "image": URLInput(attrs={"placeholder": "https://..."}),
        }