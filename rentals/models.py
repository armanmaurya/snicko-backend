from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError

User = settings.AUTH_USER_MODEL


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Item(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='items')
    name = models.CharField(max_length=255)
    description = models.TextField()
    condition_notes = models.TextField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    price_per_day = models.DecimalField(max_digits=8, decimal_places=2)
    deposit_amount = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    image = models.ImageField(upload_to='item_images/')
    is_available = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.category.name if self.category else 'No Category'}"


class Booking(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
    ]

    renter = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    item = models.ForeignKey(Item, on_delete=models.CASCADE, related_name='bookings')
    start_date = models.DateField()
    end_date = models.DateField()
    total_price = models.DecimalField(max_digits=10, decimal_places=2, editable=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    pickup_photo = models.ImageField(upload_to='pickup_photos/', null=True, blank=True)
    return_photo = models.ImageField(upload_to='return_photos/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Booking"
        verbose_name_plural = "Bookings"
        ordering = ['-created_at']

    def duration(self):
        return (self.end_date - self.start_date).days + 1

    def clean(self):
        if self.start_date < timezone.now().date():
            raise ValidationError("Start date cannot be in the past.")
        if self.end_date <= self.start_date:
            raise ValidationError("End date must be after the start date.")

    def save(self, *args, **kwargs):
        self.total_price = self.item.price_per_day * self.duration()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.item.name} booked by {self.renter.username}"


class DamageReport(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='damage_report')
    reported_by = models.ForeignKey(User, on_delete=models.CASCADE)
    description = models.TextField()
    photo = models.ImageField(upload_to='damage_reports/', null=True, blank=True)
    reported_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.booking.status not in ['ACTIVE', 'COMPLETED']:
            raise ValidationError("Damage reports can only be created for active or completed bookings")
        if self.reported_by != self.booking.item.owner and self.reported_by != self.booking.renter:
            raise ValidationError("Only the item owner or renter can create damage reports")

    def __str__(self):
        return f"Damage report for {self.booking.item.name}"
