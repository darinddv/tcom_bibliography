def user_roles(request):
    """
    Makes user role flags available in every template automatically.
    is_public is True for authenticated users with no special role.
    Anonymous users also get is_public=True.
    """
    if not request.user.is_authenticated:
        return {
            'is_contributor': False,
            'is_reviewer': False,
            'is_editor': False,
            'is_public': True,
        }

    groups = set(request.user.groups.values_list('name', flat=True))

    is_contributor = request.user.is_staff or 'Contributor' in groups
    is_reviewer = request.user.is_staff or 'Reviewer' in groups
    is_editor = request.user.is_staff or 'Editor' in groups

    return {
        'is_contributor': is_contributor,
        'is_reviewer': is_reviewer,
        'is_editor': is_editor,
        'is_public': not (is_contributor or is_reviewer or is_editor),
    }
