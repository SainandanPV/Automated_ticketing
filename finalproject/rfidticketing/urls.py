from django.urls import path
from .views import *

urlpatterns = [
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('card-details/', card_details, name='card_details'),
    path('process_rfid_data/', process_rfid_data, name='process_rfid_data'),  # Updated for processing RFID data
    path('transaction_history/', transaction_history, name='transaction_history'),  # Transaction history view
]
