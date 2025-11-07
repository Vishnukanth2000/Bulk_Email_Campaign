# campaigns/views.py
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q
from django.contrib import messages
from .models import Campaign, Recipient
from .forms import CampaignForm, RecipientUploadForm
from pydantic import BaseModel, EmailStr, ValidationError

# Pydantic model for validation
class RecipientValidator(BaseModel):
    name: str
    email: EmailStr

def campaign_dashboard(request):
    campaigns = Campaign.objects.annotate(
        total_recipients=Count('logs'),
        sent_count=Count('logs', filter=Q(logs__status='SENT')),
        failed_count=Count('logs', filter=Q(logs__status='FAILED'))
    ).order_by('-created_at')
    
    return render(request, 'campaigns/campaign_dashboard.html', {'campaigns': campaigns})

def campaign_detail(request, pk):
    campaign = get_object_or_404(Campaign, pk=pk)
    logs = campaign.logs.all().order_by('recipient__email')
    return render(request, 'campaigns/campaign_detail.html', {'campaign': campaign, 'logs': logs})

def campaign_create(request):
    if request.method == 'POST':
        form = CampaignForm(request.POST)
        if form.is_valid():
            campaign = form.save(commit=False)
            campaign.status = 'SCHEDULED' # Set status when creating
            campaign.save()
            messages.success(request, 'Campaign created and scheduled successfully!')
            return redirect('campaign_dashboard')
    else:
        form = CampaignForm()
    return render(request, 'campaigns/campaign_form.html', {'form': form})

def recipient_upload(request):
    if request.method == 'POST':
        form = RecipientUploadForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            try:
                # Use pandas to read both CSV and Excel
                df = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                
                recipients_to_create = []
                existing_emails = set(Recipient.objects.values_list('email', flat=True))

                for index, row in df.iterrows():
                    try:
                        # Validate data using Pydantic
                        validated_data = RecipientValidator(name=row['name'], email=row['email'])
                        
                        # Check for duplicates
                        if validated_data.email not in existing_emails:
                            recipients_to_create.append(
                                Recipient(name=validated_data.name, email=validated_data.email)
                            )
                            existing_emails.add(validated_data.email) # Avoid duplicates within the file

                    except ValidationError as e:
                        messages.error(request, f"Validation error in row {index + 2}: {e}")
                        return redirect('recipient_upload')
                    except KeyError:
                         messages.error(request, "File must contain 'name' and 'email' columns.")
                         return redirect('recipient_upload')

                # Use bulk_create for efficiency
                Recipient.objects.bulk_create(recipients_to_create, ignore_conflicts=True)
                messages.success(request, f'{len(recipients_to_create)} new recipients uploaded successfully.')
                return redirect('campaign_dashboard')

            except Exception as e:
                messages.error(request, f"Error processing file: {e}")
    else:
        form = RecipientUploadForm()
    return render(request, 'campaigns/recipient_upload.html', {'form': form})