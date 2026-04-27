from rest_framework.throttling import UserRateThrottle

class PremiumThrottle(UserRateThrottle):
    scope = 'premium'