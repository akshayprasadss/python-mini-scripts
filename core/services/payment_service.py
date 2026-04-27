import razorpay
from django.conf import settings

client = razorpay.Client(auth=(settings.RAZORPAY_KEY, settings.RAZORPAY_SECRET))


def create_order(amount):
    return client.order.create({
        "amount": int(amount * 100),
        "currency": "INR",
        "payment_capture": 1
    })


def verify_payment(data):
    try:
        client.utility.verify_payment_signature(data)
        return True
    except:
        return False