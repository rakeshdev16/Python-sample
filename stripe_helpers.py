import stripe
from .models import Payment
from property.models import PropertyRecord

class StripeHelper:
    @staticmethod
    def handle_checkout_session_completed(session):
        # Retrieve the payment intent from Stripe
        payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])

        # Retrieve the charge details using the latest charge from the payment intent
        if payment_intent and payment_intent['latest_charge']:
            charge = stripe.Charge.retrieve(payment_intent['latest_charge'])

            # Get card details from the charge object
            card_brand = charge['payment_method_details']['card']['brand']
            card_last4 = charge['payment_method_details']['card']['last4']
            charge_status = charge['status']  # Success or failed charge status

            # Update payment with card details and status
            StripeHelper._update_payment(session, payment_intent, card_brand, card_last4, status=charge_status)
            if charge_status == 'succeeded':
                # If payment is successful, proceed with the property transfer and record creation
                StripeHelper._complete_transfer(session)

    @staticmethod
    def handle_async_payment_succeeded(session):
        # Similar to `handle_checkout_session_completed`, save success details
        payment = Payment.objects.filter(session_id=session['id']).first()
        if payment:
            payment.status = 'succeeded'
            payment.save()
            StripeHelper._complete_transfer(session)

    @staticmethod
    def handle_async_payment_failed(session):
        payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])
        last_payment_error = payment_intent['last_payment_error']['message'] if payment_intent.get('last_payment_error') else "Unknown error"
        
        # Update payment with failure status and error message
        StripeHelper._update_payment(session, payment_intent, status='failed')

    @staticmethod
    def handle_checkout_session_expired(session):
        payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])

        # Update payment with expired status
        StripeHelper._update_payment(session, payment_intent, status='expired')

    @staticmethod
    def handle_checkout_session_canceled(session):
        payment_intent = stripe.PaymentIntent.retrieve(session['payment_intent'])

        # Update payment with canceled status
        StripeHelper._update_payment(session, payment_intent, status='canceled')

    @staticmethod
    def _update_payment(session, payment_intent, card_brand=None, card_last4=None, status=None):
        """Update the payment object with details (including failures or cancels)."""
        payment = Payment.objects.filter(session_id=session['id']).first()
        if payment:
            payment.payment_intent_id = payment_intent.id
            if card_brand:
                payment.card_brand = card_brand
            if card_last4:
                payment.card_last4 = card_last4
            if status:
                payment.status = status
            payment.save()

    @staticmethod
    def _complete_transfer(session):
        """Handles successful transfers: updating ownership and creating property records."""
        payment = Payment.objects.filter(session_id=session['id']).first()
        if payment:
            transfer_req = payment.transfer_req
            transfer_req.status = "paid"
            transfer_req.save()

            # Transfer property ownership
            property = transfer_req.property
            property.user = transfer_req.requested_by
            property.save()

            # Create property record
            PropertyRecord.objects.create(
                property=property,
                user=transfer_req.requested_by
            )



def get_or_create_stripe_customer(user):
        """Retrieve or create a Stripe customer for the user."""
        try:
            # Assuming you have a field to store Stripe customer ID
            stripe_customer_id = user.stripe_customer_id
            if stripe_customer_id:
                return stripe.Customer.retrieve(stripe_customer_id)
        except stripe.error.StripeError:
            pass  # If retrieving fails, fall back to creating a new customer
        
        # Create a new Stripe customer
        customer = stripe.Customer.create(
            email=user.email,
            name=user.get_full_name() or user.username
        )
        
        # Save the customer ID to the user's profile
        user.stripe_customer_id = customer.id
        user.save()
        
        return customer