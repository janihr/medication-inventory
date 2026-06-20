# File: models.py
from django.db import models


class UserProfile(models.Model):
    """Profile of the person using this system (for order PDFs)."""
    name = models.CharField(max_length=255, blank=True, default='', verbose_name='Full Name')
    organization = models.CharField(
        max_length=255, blank=True, default='',
        help_text='Practice, pharmacy, or company name'
    )
    address_line1 = models.CharField(max_length=255, blank=True, default='', verbose_name='Address Line 1')
    address_line2 = models.CharField(max_length=255, blank=True, default='', verbose_name='Address Line 2')
    postal_code = models.CharField(max_length=20, blank=True, default='', verbose_name='Postal Code')
    city = models.CharField(max_length=100, blank=True, default='')
    phone = models.CharField(max_length=50, blank=True, default='', verbose_name='Phone Number')
    email = models.EmailField(blank=True, default='')
    customer_number = models.CharField(
        max_length=100, blank=True, default='',
        verbose_name='Customer Number',
        help_text='Your customer number at suppliers'
    )

    class Meta:
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'

    def __str__(self):
        return self.name or 'My Profile'

    @classmethod
    def get_profile(cls):
        """Get or create the singleton profile."""
        profile, created = cls.objects.get_or_create(pk=1)
        return profile


class MedicineItem(models.Model):
    """A medication item in the catalog."""
    name = models.CharField(max_length=255)
    manufacturer = models.CharField(max_length=255, blank=True, default='')
    pzn = models.CharField(
        max_length=20,
        blank=True,
        default='',
        verbose_name='PZN',
        help_text='Pharmazentralnummer'
    )
    package_size = models.CharField(max_length=50, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Medicine Item'
        verbose_name_plural = 'Medicine Items'

    def __str__(self):
        return f"{self.name} (PZN: {self.pzn})" if self.pzn else self.name


class Supplier(models.Model):
    """A medication supplier."""
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=50, blank=True, default='')
    email = models.EmailField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Supplier'
        verbose_name_plural = 'Suppliers'

    def __str__(self):
        return self.name


class Order(models.Model):
    """An order placed with a supplier."""

    class Status(models.TextChoices):
        OPEN = 'open', 'Open'
        ORDERED = 'ordered', 'Ordered'
        RECEIVED = 'received', 'Received'
        CANCELED = 'canceled', 'Canceled'

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='orders'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.OPEN
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Order'
        verbose_name_plural = 'Orders'

    def __str__(self):
        return f"Order #{self.pk} — {self.supplier.name} ({self.get_status_display()})"

    @property
    def order_id(self):
        """Formatted order ID."""
        return f"ORD-{self.pk:05d}"

    @property
    def total_items(self):
        """Total number of item lines in this order."""
        return self.items.count()


class OrderItem(models.Model):
    """A single line item within an order."""
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='items'
    )
    medicine_item = models.ForeignKey(
        MedicineItem,
        on_delete=models.PROTECT,
        related_name='order_items'
    )
    amount = models.PositiveIntegerField(default=1)
    note = models.TextField(blank=True, default='')

    class Meta:
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
        unique_together = ['order', 'medicine_item']

    def __str__(self):
        return f"{self.medicine_item.name} x{self.amount}"


# Append to models.py

class BackupSettings(models.Model):
    """Singleton model for backup configuration."""
    
    class Schedule(models.TextChoices):
        DISABLED = 'disabled', 'Disabled'
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    schedule = models.CharField(
        max_length=20,
        choices=Schedule.choices,
        default=Schedule.DISABLED,
        help_text='How often automatic backups should run'
    )
    retention_days = models.PositiveIntegerField(
        default=30,
        help_text='Delete backups older than this many days (0 = keep forever)'
    )
    backup_dir = models.CharField(
        max_length=500,
        default='/app/backups',
        help_text='Directory where backup files are stored'
    )
    last_backup_at = models.DateTimeField(null=True, blank=True)
    last_backup_file = models.CharField(max_length=500, blank=True, default='')
    last_backup_status = models.CharField(max_length=50, blank=True, default='')

    class Meta:
        verbose_name = 'Backup Settings'
        verbose_name_plural = 'Backup Settings'

    def __str__(self):
        return f"Backup Settings (Schedule: {self.get_schedule_display()})"

    @classmethod
    def get_settings(cls):
        """Get or create singleton settings."""
        settings, created = cls.objects.get_or_create(pk=1)
        return settings