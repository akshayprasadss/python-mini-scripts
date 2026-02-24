class RoleLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        print("Middleware executed")  # TEMP TEST

        if request.user.is_authenticated:
            print(f"User: {request.user.email} | Role: {request.user.role}")

        response = self.get_response(request)
        return response
