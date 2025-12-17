from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import Policy, UserGroup, PolicyAudience


def policy_list(request):
    all_policies = Policy.objects.all().order_by('-created_at')

    paginator = Paginator(all_policies, 6)  # 6 Policies فقط
    page_number = request.GET.get('page')
    policies = paginator.get_page(page_number)

    return render(request, 'policy/policy.html', {
        'policies': policies
    })


def policy_detail(request, id):
    policy = get_object_or_404(Policy, id=id)
    return render(request, 'policy/policy_detail.html', {
        'policy': policy
    })


def create_policy(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        group_id = request.POST.get('group')

        policy = Policy.objects.create(
            title=title,
            description=description,
            is_published=True
        )

        if group_id:
            group = get_object_or_404(UserGroup, id=group_id)
            PolicyAudience.objects.create(
                policy=policy,
                group=group
            )

        return redirect('policies:policy_list')  # ✅ رجوع لصفحة السياسات

    groups = UserGroup.objects.all()
    return render(request, 'policy/create_policy.html', {
        'groups': groups
    })


def policy_acknowledge(request):
    return render(request, 'policy/policy_acknow.html')
