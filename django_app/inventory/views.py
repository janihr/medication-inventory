# File: views.py
import json
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.urls import reverse
from .pdf import generate_order_pdf

from .models import MedicineItem, Supplier, Order, OrderItem, UserProfile
from .forms import (
    MedicineItemForm,
    SupplierForm,
    OrderCreateForm,
    OrderStatusForm,
    OrderItemForm,
    OrderItemFormSet,
    UserProfileForm,
)


# === User Profile ===

def profile_edit(request):
    """Edit the user profile (singleton)."""
    profile = UserProfile.get_profile()
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('inventory:profile')
    else:
        form = UserProfileForm(instance=profile)
    return render(request, 'inventory/profile_form.html', {'form': form})


# === Dashboard ===

def dashboard(request):
    """Landing page - dashboard with overview counts."""
    context = {
        'medicine_count': MedicineItem.objects.count(),
        'supplier_count': Supplier.objects.count(),
        'order_count': Order.objects.count(),
        'open_orders': Order.objects.filter(status=Order.Status.OPEN).count(),
        'recent_orders': Order.objects.select_related('supplier')[:5],
    }
    return render(request, 'inventory/dashboard.html', context)


# === Medicine Items ===

def medicine_list(request):
    """List all medicine items."""
    items = MedicineItem.objects.all()
    query = request.GET.get('q', '')
    if query:
        items = items.filter(name__icontains=query)
    return render(request, 'inventory/medicine_list.html', {'items': items, 'query': query})


def medicine_create(request):
    """Create a new medicine item."""
    if request.method == 'POST':
        form = MedicineItemForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine item created successfully.')
            return redirect('inventory:medicine_list')
    else:
        form = MedicineItemForm()
    return render(request, 'inventory/medicine_form.html', {'form': form, 'title': 'Add Medicine Item'})


def medicine_edit(request, pk):
    """Edit an existing medicine item."""
    item = get_object_or_404(MedicineItem, pk=pk)
    if request.method == 'POST':
        form = MedicineItemForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, 'Medicine item updated successfully.')
            return redirect('inventory:medicine_list')
    else:
        form = MedicineItemForm(instance=item)
    return render(request, 'inventory/medicine_form.html', {'form': form, 'title': 'Edit Medicine Item'})


def medicine_delete(request, pk):
    """Delete a medicine item."""
    item = get_object_or_404(MedicineItem, pk=pk)
    if request.method == 'POST':
        try:
            item.delete()
            messages.success(request, f'"{item.name}" deleted successfully.')
        except Exception:
            messages.error(request, 'Cannot delete: item is referenced in orders.')
        return redirect('inventory:medicine_list')
    return render(request, 'inventory/confirm_delete.html', {'object': item, 'type': 'Medicine Item'})


# === Suppliers ===

def supplier_list(request):
    """List all suppliers."""
    suppliers = Supplier.objects.all()
    query = request.GET.get('q', '')
    if query:
        suppliers = suppliers.filter(name__icontains=query)
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers, 'query': query})


def supplier_create(request):
    """Create a new supplier."""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier created successfully.')
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm()
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'Add Supplier'})


def supplier_edit(request, pk):
    """Edit an existing supplier."""
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        form = SupplierForm(request.POST, instance=supplier)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier updated successfully.')
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm(instance=supplier)
    return render(request, 'inventory/supplier_form.html', {'form': form, 'title': 'Edit Supplier'})


def supplier_delete(request, pk):
    """Delete a supplier."""
    supplier = get_object_or_404(Supplier, pk=pk)
    if request.method == 'POST':
        try:
            supplier.delete()
            messages.success(request, f'"{supplier.name}" deleted successfully.')
        except Exception:
            messages.error(request, 'Cannot delete: supplier is referenced in orders.')
        return redirect('inventory:supplier_list')
    return render(request, 'inventory/confirm_delete.html', {'object': supplier, 'type': 'Supplier'})


# === Orders ===

def order_list(request):
    """List all orders with optional status filter."""
    orders = Order.objects.select_related('supplier').all()
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)
    return render(request, 'inventory/order_list.html', {
        'orders': orders,
        'status_filter': status_filter,
        'status_choices': Order.Status.choices,
    })


def order_create(request):
    """Create a new order (status = open)."""
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            order.status = Order.Status.OPEN
            order.save()
            messages.success(request, f'Order {order.order_id} created. Now add items.')
            return redirect('inventory:order_fill', pk=order.pk)
    else:
        form = OrderCreateForm()
    return render(request, 'inventory/order_create.html', {'form': form})


def order_detail(request, pk):
    """View order details."""
    order = get_object_or_404(Order.objects.select_related('supplier'), pk=pk)
    items = order.items.select_related('medicine_item').all()
    status_form = OrderStatusForm(instance=order)
    return render(request, 'inventory/order_detail.html', {
        'order': order,
        'items': items,
        'status_form': status_form,
    })


def order_fill(request, pk):
    """Add/edit items in an open order."""
    order = get_object_or_404(Order, pk=pk)

    if order.status != Order.Status.OPEN:
        messages.warning(request, 'Only open orders can be modified.')
        return redirect('inventory:order_detail', pk=order.pk)

    if request.method == 'POST':
        formset = OrderItemFormSet(request.POST, instance=order)
        if formset.is_valid():
            formset.save()
            messages.success(request, 'Order items updated.')
            return redirect('inventory:order_detail', pk=order.pk)
    else:
        formset = OrderItemFormSet(instance=order)

    medicine_items = list(
        MedicineItem.objects.values('id', 'name', 'pzn', 'package_size')
    )
    medicine_items_json = json.dumps(medicine_items)

    return render(request, 'inventory/order_fill.html', {
        'order': order,
        'formset': formset,
        'medicine_items_json': medicine_items_json,
    })


def order_status(request, pk):
    """Change order status via action buttons."""
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        new_status = request.POST.get('new_status')
        allowed_transitions = {
            Order.Status.OPEN: [Order.Status.ORDERED, Order.Status.CANCELED],
            Order.Status.ORDERED: [Order.Status.OPEN, Order.Status.RECEIVED, Order.Status.CANCELED],
        }
        allowed = allowed_transitions.get(order.status, [])
        if new_status in allowed:
            order.status = new_status
            order.save()
            messages.success(request, f'Order {order.order_id} status changed to "{order.get_status_display()}".')
        else:
            messages.error(request, 'Invalid status transition.')
    return redirect('inventory:order_detail', pk=order.pk)


def order_delete(request, pk):
    """Delete an order."""
    order = get_object_or_404(Order, pk=pk)
    if request.method == 'POST':
        order_id = order.order_id
        order.delete()
        messages.success(request, f'Order {order_id} deleted.')
        return redirect('inventory:order_list')
    return render(request, 'inventory/confirm_delete.html', {'object': order, 'type': 'Order'})


def order_pdf(request, pk):
    """Export order as PDF."""
    order = get_object_or_404(Order.objects.select_related('supplier'), pk=pk)
    return generate_order_pdf(order)