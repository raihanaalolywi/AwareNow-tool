from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from .models import Policy, PolicyAudience, CompanyGroup, PolicyAcknowledgement
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from account.models import User
from django.contrib import messages
from django.db.models import Q

# @login_required
# def policy_list(request):
#     user = request.user

#     if user.role == "EMPLOYEE":
#         user_groups = user.company_groups.all()

#         policies = Policy.objects.filter(
#             is_published=True,
#             groups__in=user_groups
#         ).distinct()

#     else:
#         policies = Policy.objects.filter(is_published=True)

#     paginator = Paginator(policies.order_by('-created_at'), 6)
#     page_number = request.GET.get('page')
#     policies = paginator.get_page(page_number)

#     return render(request, 'policies/policy.html', {
#         'policies': policies
#     })

# @login_required
# def policy_detail(request, id):
#     policy = get_object_or_404(Policy, id=id)

#     if request.user.role != "COMPANY_ADMIN":
#         return redirect("account:platform-login")

#     acknowledgements = policy.acknowledgements.select_related('user')

#     return render(request, 'policy/policy_detail.html', {
#         'policy': policy,
#         'acknowledgements': acknowledgements
#     })

@login_required
def create_policy(request):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    company = request.user.company
    groups = CompanyGroup.objects.filter(company=company, is_system=False)

    if request.method == "POST":
        title = request.POST.get("title")
        description = request.POST.get("description")
        audience = request.POST.get("audience")  # all | groups
        group_ids = request.POST.getlist("groups")

        policy = Policy.objects.create(
            title=title,
            description=description,
            is_published=True
        )

        if audience == "groups":
            for group_id in group_ids:
                PolicyAudience.objects.create(
                    policy=policy,
                    group_id=group_id
                )

        messages.success(request, "Policy created successfully")
        return redirect("policies:company_policies")

    return render(request, "policies/create_policy.html", {
        "groups": groups
    })

@login_required
def policy_acknowledge(request, id):
    policy = get_object_or_404(Policy, id=id)
    user = request.user

    if user.role != "EMPLOYEE":
        return redirect('policies:policy_list')

    already_acknowledged = PolicyAcknowledgement.objects.filter(
        policy=policy,
        user=user
    ).exists()

    if request.method == 'POST' and not already_acknowledged:
        PolicyAcknowledgement.objects.create(
            policy=policy,
            user=user
        )

    return redirect('policies:employee_policies')


@login_required
def employee_policies(request):
    if request.user.role != "EMPLOYEE":
        return redirect("account:platform-login")

    user = request.user
    user_groups = user.company_groups.all()

    policies = Policy.objects.filter(
        is_published=True,
        ).filter(
            Q(groups__in=user_groups) | Q(groups__isnull=True)
        ).distinct()

    acknowledged_ids = set(
        PolicyAcknowledgement.objects.filter(
            user=user
        ).values_list('policy_id', flat=True)
    )

    return render(request, 'policies/employee_policy_list.html', {
        'policies': policies,
        'acknowledged_ids': acknowledged_ids,
    })

@login_required
def company_policy_dashboard(request):
    if request.user.role != "COMPANY_ADMIN":
        return redirect("account:platform-login")

    company = request.user.company

    policies = Policy.objects.filter(is_published=True).prefetch_related(
        'groups',
        'acknowledgements'
    )

    policy_data = []

    for policy in policies:
        # employees in scope
        if policy.groups.exists():
            employees = User.objects.filter(
                company=company,
                role='EMPLOYEE',
                company_groups__in=policy.groups.all()
            ).distinct()
            audience = ", ".join(policy.groups.values_list('name', flat=True))
        else:
            employees = User.objects.filter(
                company=company,
                role='EMPLOYEE'
            )
            audience = "All Employees"

        total = employees.count()
        ack_users = set(
            PolicyAcknowledgement.objects.filter(policy=policy)
            .values_list('user_id', flat=True)
        )

        acknowledged = len(
            ack_users.intersection(employees.values_list('id', flat=True))
        )

        policy_data.append({
            'policy': policy,
            'audience': audience,
            'total': total,
            'acknowledged': acknowledged,
            'employees': employees,
            'ack_users': ack_users,
        })

    return render(request, "policies/company_policy_dashboard.html", {
        'policies': policy_data
    })