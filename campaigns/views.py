from django.shortcuts import render

def phishing_page(request):
    return render(request, "campaigns/phishing.html")