from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .forms import RegistrationForm, RechargeForm
from .models import RFIDCard, UserProfile, RFIDCardLog
import json
import logging
from decimal import Decimal
from django.utils import timezone

logger = logging.getLogger(__name__)

def home(request):
    if request.user.is_authenticated:
        return redirect('card_details')
    return render(request, 'home.html')

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('card_details')
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})

def register_view(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.create(
                user=user,
                age=form.cleaned_data['age'],
                phone_number=form.cleaned_data['phone_number']
            )
            RFIDCard.objects.create(user=user)
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'register.html', {'form': form})

@login_required
def card_details(request):
    card = RFIDCard.objects.get(user=request.user)
    if request.method == 'POST':
        form = RechargeForm(request.POST)
        if form.is_valid():
            card.balance += form.cleaned_data['amount']
            card.save()
            return redirect('card_details')
    else:
        form = RechargeForm()
    return render(request, 'card_details.html', {'card': card, 'form': form})





@csrf_exempt
def process_rfid_data(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            rfid_uid = data.get('rfid_uid')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            passenger_count = data.get('passenger_count', 1)  # Default to 1 if not provided

            if not rfid_uid or latitude is None or longitude is None:
                return JsonResponse({"status": "error", "message": "Incomplete data received"}, status=400)

            try:
                card = RFIDCard.objects.get(uid=rfid_uid)
            except ObjectDoesNotExist:
                return JsonResponse({"status": "error", "message": "RFID card not found"}, status=404)

            if card.balance < 20:
                return JsonResponse({"status": "error", "message": "Insufficient balance to start journey"}, status=402)

            # Check for an existing entry with no exit recorded
            existing_transaction = RFIDCardLog.objects.filter(
                rfid_card=card, exit_latitude__isnull=True
            ).first()

            if not existing_transaction:
                # Create a new entry record
                RFIDCardLog.objects.create(
                    rfid_card=card,
                    entry_latitude=latitude,
                    entry_longitude=longitude,
                    passenger_count=passenger_count,
                )
                return JsonResponse({"status": "success", "message": "Entry recorded"})
            else:
                # Update the existing transaction with exit details
                existing_transaction.exit_latitude = latitude
                existing_transaction.exit_longitude = longitude
                existing_transaction.exit_timestamp = timezone.now()

                fare = existing_transaction.calculate_amount()

                if fare <= card.balance:
                    card.balance -= fare
                    card.save()

                    existing_transaction.fare_deducted = fare
                    existing_transaction.save()

                    return JsonResponse({"status": "success", "message": "Exit recorded", "fare": float(fare)})
                else:
                    return JsonResponse({"status": "error", "message": "Insufficient balance"}, status=402)

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON format"}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


@login_required
def transaction_history(request):
    try:
        rfid_card = RFIDCard.objects.get(user=request.user)

        transactions = RFIDCardLog.objects.filter(
            rfid_card=rfid_card, exit_latitude__isnull=False
        ).order_by('-entry_timestamp')

        for transaction in transactions:
            transaction.distance = transaction.calculate_distance()
            transaction.fare = transaction.fare_deducted or 0  

        user_info = {
            'uid': rfid_card.uid if rfid_card.uid else "Not Assigned",  # Ensure valid UID
            'name': request.user.get_full_name() or request.user.username
        }

    except RFIDCard.DoesNotExist:
        transactions = []
        user_info = {'uid': "Not Assigned", 'name': request.user.get_full_name() or request.user.username}

    return render(request, 'transaction_history.html', {'transactions': transactions, 'user': user_info})
