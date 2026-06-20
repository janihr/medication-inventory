# File: admin.py
from django.contrib import admin
from .models import MedicineItem, Supplier, Order, OrderItem, UserProfile, BackupSettings


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['name', 'organization', 'city', 'phone', 'email']


@admin.register(MedicineItem)
class MedicineItemAdmin(admin.ModelAdmin):
    list_display = ['name', 'manufacturer', 'pzn', 'package_size', 'created_at']
    search_fields = ['name', 'pzn', 'manufacturer']
    list_filter = ['manufacturer']


@admin.register(Supplier)
class SupplierAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone_number', 'email', 'created_at']
    search_fields = ['name', 'email']


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    autocomplete_fields = ['medicine_item']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'supplier', 'status', 'total_items', 'created_at']
    list_filter = ['status', 'supplier']
    search_fields = ['supplier__name']
    inlines = [OrderItemInline]
    readonly_fields = ['created_at', 'updated_at']


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'medicine_item', 'amount', 'note']
    list_filter = ['order__status']
    search_fields = ['medicine_item__name']


@admin.register(BackupSettings)
class BackupSettingsAdmin(admin.ModelAdmin):
    list_display = ['schedule', 'retention_days', 'last_backup_at', 'last_backup_status']
    readonly_fields = ['last_backup_at', 'last_backup_file', 'last_backup_status']
    fieldsets = (
        ('Schedule Configuration', {
            'fields': ('schedule', 'retention_days', 'backup_dir'),
        }),
        ('Last Backup Info (read-only)', {
            'fields': ('last_backup_at', 'last_backup_file', 'last_backup_status'),
            'classes': ('collapse',),
        }),
    )

    def has_add_permission(self, request):
        # Singleton: only allow one instance
        if self.model.objects.exists():
            return False
        return super().has_add_permission(request)

    def has_delete_permission(self, request, obj=None):
        return False