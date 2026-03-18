def user_roles(request):
    """
    Makes user role flags available in every template automatically.
    """
    if not request.user.is_authenticated:
        return {
            'is_contributor': False,
            'is_reviewer': False,
            'is_editor': False,
        }

    groups = set(request.user.groups.values_list('name', flat=True))

    return {
        'is_contributor': request.user.is_staff or 'Contributor' in groups,
        'is_reviewer': request.user.is_staff or 'Reviewer' in groups,
        'is_editor': request.user.is_staff or 'Editor' in groups,
    }