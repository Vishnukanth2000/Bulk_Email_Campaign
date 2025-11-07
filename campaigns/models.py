# campaigns/models.py
from django.db import models

class Recipient(models.Model):
    class SubscriptionStatus(models.TextChoices):
        SUBSCRIBED = 'SUBSCRIBED', 'Subscribed'
        UNSUBSCRIBED = 'UNSUBSCRIBED', 'Unsubscribed'

    name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.SUBSCRIBED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Campaign(models.Model):
    class CampaignStatus(models.TextChoices):
        DRAFT = 'DRAFT', 'Draft'
        SCHEDULED = 'SCHEDULED', 'Scheduled'
        IN_PROGRESS = 'IN_PROGRESS', 'In Progress'
        COMPLETED = 'COMPLETED', 'Completed'
        FAILED = 'FAILED', 'Failed'

    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    content = models.TextField() # Can be plain text or HTML
    scheduled_time = models.DateTimeField()
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class DeliveryLog(models.Model):
    class DeliveryStatus(models.TextChoices):
        PENDING = 'PENDING', 'Pending'
        SENT = 'SENT', 'Sent'
        FAILED = 'FAILED', 'Failed'

    campaign = models.ForeignKey(Campaign, related_name='logs', on_delete=models.CASCADE)
    recipient = models.ForeignKey(Recipient, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING
    )
    sent_at = models.DateTimeField(null=True, blank=True)
    failure_reason = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('campaign', 'recipient') # One log per recipient per campaign

    def __str__(self):
        return f"{self.campaign.name} -> {self.recipient.email}: {self.status}"