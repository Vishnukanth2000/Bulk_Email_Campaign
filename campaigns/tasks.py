# campaigns/tasks.py
import csv
from io import StringIO
from celery import shared_task
from django.utils import timezone
from django.core.mail import EmailMessage
from django.conf import settings
from .models import Campaign, Recipient, DeliveryLog

@shared_task
def send_campaign_email(log_id):
    """Sends a single email for a given delivery log."""
    try:
        log = DeliveryLog.objects.get(id=log_id)
        # Prevent re-sending
        if log.status == 'SENT':
            return f"Log {log_id} already sent."

        recipient = log.recipient
        campaign = log.campaign
        
        # ==========================================================
        # === SIMULATION CODE TO TEST FAILURE (தற்காலிக சோதனை குறியீடு) ===
        # This code will cause an error if the email contains "failmail".
        # (மின்னஞ்சலில் "failmail" இருந்தால் இந்த குறியீடு ஒரு பிழையை ஏற்படுத்தும்.)
        if 'failmail' in recipient.email:
            raise ValueError("Simulated email failure for testing purposes.")
        # ==========================================================

        email = EmailMessage(
            subject=campaign.subject,
            body=campaign.content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient.email],
        )
        email.content_subtype = "html" # if you send HTML content
        email.send()

        log.status = DeliveryLog.DeliveryStatus.SENT
        log.sent_at = timezone.now()
        log.save()
        
        return f"Email to {recipient.email} sent successfully."
    except DeliveryLog.DoesNotExist:
        return f"DeliveryLog with id {log_id} not found."
    except Exception as e:
        if 'log' in locals():
            log.status = DeliveryLog.DeliveryStatus.FAILED
            log.failure_reason = str(e)
            log.save()
        return f"Failed to send email for log {log_id}: {str(e)}"

@shared_task
def process_campaign(campaign_id):
    """Processes a campaign by creating logs and queueing individual email tasks."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        campaign.status = Campaign.CampaignStatus.IN_PROGRESS
        campaign.save()

        subscribed_recipients = Recipient.objects.filter(status=Recipient.SubscriptionStatus.SUBSCRIBED)
        
        # Create all delivery logs in bulk
        logs_to_create = [
            DeliveryLog(campaign=campaign, recipient=recipient)
            for recipient in subscribed_recipients
        ]
        DeliveryLog.objects.bulk_create(logs_to_create, ignore_conflicts=True)

        # Get all pending logs for this campaign and queue them
        pending_logs = DeliveryLog.objects.filter(campaign=campaign, status=DeliveryLog.DeliveryStatus.PENDING)
        for log in pending_logs:
            send_campaign_email.delay(log.id)

        # Schedule a task to check for completion and send report
        check_campaign_completion.apply_async(args=[campaign_id], countdown=60) # Check in 1 minute

    except Campaign.DoesNotExist:
        # Handle case where campaign is deleted before processing
        pass

@shared_task
def check_campaign_completion(campaign_id):
    """Checks if a campaign is complete and triggers the report if it is."""
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        pending_count = campaign.logs.filter(status=DeliveryLog.DeliveryStatus.PENDING).count()

        if pending_count == 0:
            # All tasks are done (either SENT or FAILED)
            campaign.status = Campaign.CampaignStatus.COMPLETED
            campaign.save()
            generate_and_send_report.delay(campaign_id)
        else:
            # Re-queue the check for later
            check_campaign_completion.apply_async(args=[campaign_id], countdown=60) # Check again in 1 minute

    except Campaign.DoesNotExist:
        pass


@shared_task
def generate_and_send_report(campaign_id):
    """Generates a CSV report and emails it to the admin."""
    campaign = Campaign.objects.get(id=campaign_id)
    logs = campaign.logs.all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(['Recipient Email', 'Status', 'Sent At', 'Failure Reason'])

    for log in logs:
        writer.writerow([
            log.recipient.email,
            log.status,
            log.sent_at.strftime("%Y-%m-%d %H:%M:%S") if log.sent_at else '',
            log.failure_reason or ''
        ])
    
    csv_file = output.getvalue()
    output.close()

    email = EmailMessage(
        subject=f"Campaign Report: {campaign.name}",
        body=f"Attached is the delivery report for the campaign '{campaign.name}'.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.ADMIN_EMAIL],
    )
    email.attach(f'{campaign.name}_report.csv', csv_file, 'text/csv')
    email.send()


@shared_task
def check_and_schedule_campaigns():
    """
    This is the periodic task run by Celery Beat.
    It checks for campaigns that are scheduled and ready to be sent.
    """
    now = timezone.now()
    campaigns_to_run = Campaign.objects.filter(
        status=Campaign.CampaignStatus.SCHEDULED,
        scheduled_time__lte=now
    )
    for campaign in campaigns_to_run:
        process_campaign.delay(campaign.id)
    return f"Checked for campaigns at {now}. Found {campaigns_to_run.count()} to process."