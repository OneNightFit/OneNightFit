from django import forms
from django.forms import ModelForm, TextInput, Textarea, URLInput, Select

from catalog.models import Product


class ProductForm(ModelForm):
    image_source = forms.ChoiceField(
        choices=(("url", "URL gambar"), ("upload", "Unggah file")),
        required=False,
        initial="url",
        widget=forms.RadioSelect,
    )
    image_upload = forms.ImageField(
        label="Pilih file gambar",
        required=False,
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
    )

    class Meta:
        model = Product
        fields = [
            "name",
            "category",
            "size",
            "description",
            "price",
            "image_source",
            "image",
            "image_upload",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk and self.instance.image_file:
            self.fields["image_source"].initial = "upload"

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["image_source"] = cleaned_data.get("image_source") or "url"
        return cleaned_data

    def save(self, commit=True):
        product = super().save(commit=False)
        source = self.cleaned_data.get("image_source", "url")
        uploaded_image = self.cleaned_data.get("image_upload")

        if source == "upload":
            product.image = ""
            if uploaded_image:
                product.image_file = uploaded_image
        else:
            product.image_file = ""

        if commit:
            product.save()
            self.save_m2m()
        else:
            self.save_m2m = self._save_m2m
        return product
