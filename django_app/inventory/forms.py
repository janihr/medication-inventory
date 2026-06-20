# File: forms.py
from django import forms
from .models import MedicineItem, Supplier, Order, OrderItem, UserProfile


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = [
            'name', 'organization', 'address_line1', 'address_line2',
            'postal_code', 'city', 'phone', 'email', 'customer_number'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your full name'}),
            'organization': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Practice / Pharmacy / Company'}),
            'address_line1': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Street and number'}),
            'address_line2': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Additional address info'}),
            'postal_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 10115'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+49 ...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'customer_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Your customer number'}),
        }


class MedicineItemForm(forms.ModelForm):
    class Meta:
        model = MedicineItem
        fields = ['name', 'manufacturer', 'pzn', 'package_size']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Medicine name'}),
            'manufacturer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Manufacturer'}),
            'pzn': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 12345678'}),
            'package_size': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 100 St.'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Medicine name is required.')
        return name

    def clean_pzn(self):
        pzn = self.cleaned_data.get('pzn', '').strip()
        if pzn:
            cleaned_pzn = pzn.replace(' ', '').replace('-', '')
            if not cleaned_pzn.isdigit():
                raise forms.ValidationError('PZN must contain only digits.')
            if len(cleaned_pzn) < 7 or len(cleaned_pzn) > 8:
                raise forms.ValidationError('PZN must be 7 or 8 digits.')
            return cleaned_pzn
        return pzn


class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone_number', 'email']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Supplier name'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+49 ...'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'email@example.com'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if not name:
            raise forms.ValidationError('Supplier name is required.')
        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number', '').strip()
        if phone:
            allowed_chars = set('0123456789 +-()')
            if not all(c in allowed_chars for c in phone):
                raise forms.ValidationError('Phone number contains invalid characters.')
        return phone


class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['supplier']
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
        }

    def clean_supplier(self):
        supplier = self.cleaned_data.get('supplier')
        if not supplier:
            raise forms.ValidationError('Please select a supplier.')
        return supplier


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.status == Order.Status.OPEN:
            self.fields['status'].choices = [
                (Order.Status.ORDERED, 'Ordered'),
                (Order.Status.CANCELED, 'Canceled'),
            ]
        elif self.instance and self.instance.status == Order.Status.ORDERED:
            self.fields['status'].choices = [
                (Order.Status.OPEN, 'Open'),
                (Order.Status.RECEIVED, 'Received'),
                (Order.Status.CANCELED, 'Canceled'),
            ]
        else:
            self.fields['status'].choices = [
                (self.instance.status, self.instance.get_status_display())
            ]


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['medicine_item', 'amount', 'note']
        widgets = {
            'medicine_item': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '1', 'value': '1'}),
            'note': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional note'}),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount < 1:
            raise forms.ValidationError('Amount must be at least 1.')
        return amount

    def validate_unique(self):
        """Skip unique_together validation at the individual form level."""
        pass


class BaseOrderItemFormSet(forms.BaseInlineFormSet):
    def add_fields(self, form, index):
        """Override DELETE widget to be a hidden input (controlled via JS)."""
        super().add_fields(form, index)
        if 'DELETE' in form.fields:
            form.fields['DELETE'].widget = forms.HiddenInput()

    def clean(self):
        """Prevent duplicate medicine items across non-deleted forms."""
        super().clean()
        if any(self.errors):
            return

        seen_medicine_ids = []
        for form in self.forms:
            if self.can_delete and self._should_delete_form(form):
                continue
            if not form.cleaned_data:
                continue
            medicine_item = form.cleaned_data.get('medicine_item')
            if not medicine_item:
                continue
            if medicine_item.pk in seen_medicine_ids:
                raise forms.ValidationError(
                    'Each medicine item can only appear once per order. '
                    'Please remove duplicate selections.'
                )
            seen_medicine_ids.append(medicine_item.pk)


OrderItemFormSet = forms.inlineformset_factory(
    Order,
    OrderItem,
    form=OrderItemForm,
    formset=BaseOrderItemFormSet,
    extra=1,
    can_delete=True,
)