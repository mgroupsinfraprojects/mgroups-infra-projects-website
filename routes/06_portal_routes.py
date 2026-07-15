# M-GROUPS Portal / My Workspace routes. Executed by app.py in application globals.
# V15.6.1: module boxes now open module hub pages instead of dumping users directly into the old admin pages.

@app.route('/portal')
@login_required
def portal_workspace():
    modules = allowed_modules()
    return render_template('portal/workspace.html', modules=modules, user=current_admin(), role_label=role_label)


@app.route('/portal/web')
@login_required
@permission_required('website_view')
def portal_web():
    # Website module hub. The Website box only opens this module page.
    # Each card below has its own permission, so a manager/supervisor can be
    # given Website access without automatically seeing every website tool.
    quick_cards = [
        {
            'title': 'Public Website Preview',
            'description': 'Open the published public website to check what visitors see.',
            'url': '/',
            'permission': 'website_view',
            'icon': '🌐',
        },
        {
            'title': 'Live Editor',
            'description': 'Edit public website text directly from the page preview.',
            'url': '/admin/live-edit?page=home&module=website',
            'permission': 'website_live_edit',
            'icon': '✍️',
        },
        {
            'title': 'Website Settings',
            'description': 'Company profile, SEO, contact details and public business information.',
            'url': '/admin/settings?module=website',
            'permission': 'website_settings_edit',
            'icon': '⚙️',
        },
        {
            'title': 'Design Center',
            'description': 'Control theme, colors, fonts, buttons and homepage section visibility.',
            'url': '/admin/appearance?module=website',
            'permission': 'design_edit',
            'icon': '🎨',
        },
        {
            'title': 'About & Experience',
            'description': 'Company description, mission, vision, values and experience summary.',
            'url': '/admin/about?module=website',
            'permission': 'website_about_edit',
            'icon': '🏢',
        },
        {
            'title': 'Services',
            'description': 'Add, edit and publish service cards.',
            'url': '/admin/services?module=website',
            'permission': 'website_services_edit',
            'icon': '🧱',
        },
        {
            'title': 'Projects / Works',
            'description': 'Maintain project records, descriptions and project images.',
            'url': '/admin/projects?module=website',
            'permission': 'website_projects_edit',
            'icon': '🏗️',
        },
        {
            'title': 'Gallery',
            'description': 'Publish or hide site/work photos and captions.',
            'url': '/admin/gallery?module=website',
            'permission': 'website_gallery_edit',
            'icon': '🖼️',
        },
        {
            'title': 'Media Library',
            'description': 'Upload and reuse images for website content.',
            'url': '/admin/media?module=website',
            'permission': 'media_edit',
            'icon': '📁',
        },
    ]
    cards = [c for c in quick_cards if has_permission(c['permission'])]
    return render_template(
        'portal/module_hub.html',
        module_title='Website Management',
        module_kicker='Portal Module',
        module_description='Website tools are separated from Stock, Users, GST and System. Only allowed website actions are shown here.',
        cards=cards,
        back_url=url_for('portal_workspace'),
        notice=None if cards else 'Your role can open Website, but no website action permissions are enabled yet. Ask the Developer/Company Owner to enable specific website actions.',
    )


@app.route('/portal/stock')
@login_required
@permission_required('stock_view')
def portal_stock():
    quick_cards = [
        {'title': 'Stock Dashboard', 'description': 'Stock overview will appear here after stock integration.', 'url': '#', 'permission': 'stock_view', 'icon': '📦'},
        {'title': 'Materials', 'description': 'Material master and units.', 'url': '#', 'permission': 'stock_view', 'icon': '🧾'},
        {'title': 'Stock In / Receive', 'description': 'Purchase receive and store-in entries.', 'url': '#', 'permission': 'stock_add', 'icon': '➕'},
        {'title': 'Transfers', 'description': 'Store-to-site and site-to-site transfers.', 'url': '#', 'permission': 'stock_transfer', 'icon': '🚚'},
        {'title': 'Stock Reports', 'description': 'Stock balance, movement and low-stock reports.', 'url': '#', 'permission': 'stock_reports', 'icon': '📊'},
    ]
    cards = [c for c in quick_cards if has_permission(c['permission'])]
    return render_template(
        'portal/module_hub.html',
        module_title='Stock Management',
        module_kicker='Pending Integration',
        module_description='This is the protected stock module space. Your stock ZIP will be integrated here next under the same login and permission system.',
        cards=cards,
        back_url=url_for('portal_workspace'),
        notice='Stock pages are placeholders until the stock management ZIP is converted into /portal/stock routes.',
    )


@app.route('/portal/employees')
@login_required
@permission_required('employees_view')
def portal_employees():
    cards = [
        {'title': 'Employee List', 'description': 'Employee records and contact details.', 'url': '#', 'permission': 'employees_view', 'icon': '👥'},
        {'title': 'Attendance', 'description': 'Attendance module placeholder.', 'url': '#', 'permission': 'employees_edit', 'icon': '🗓️'},
        {'title': 'Work Records', 'description': 'Daily work and assignment records.', 'url': '#', 'permission': 'employees_edit', 'icon': '📝'},
        {'title': 'Employee Reports', 'description': 'Employee related reports.', 'url': '#', 'permission': 'reports_view', 'icon': '📊'},
    ]
    cards = [c for c in cards if has_permission(c['permission'])]
    return render_template(
        'portal/module_hub.html',
        module_title='Employee Management',
        module_kicker='Future Module',
        module_description='Employee records, attendance, roles and work details will be handled here later.',
        cards=cards,
        back_url=url_for('portal_workspace'),
        notice='Employee module is not integrated yet.',
    )


@app.route('/portal/gst')
@login_required
@permission_required('gst_view')
def portal_gst():
    cards = [
        {'title': 'GST Dashboard', 'description': 'GST summary and audit dashboard.', 'url': '#', 'permission': 'gst_view', 'icon': '🧾'},
        {'title': 'Invoice Upload', 'description': 'Upload GST invoice files for checking.', 'url': '#', 'permission': 'gst_upload', 'icon': '⬆️'},
        {'title': 'Audit Checks', 'description': 'Duplicate, mismatch and tax checks.', 'url': '#', 'permission': 'gst_view', 'icon': '🔍'},
        {'title': 'GST Reports', 'description': 'GST reports and exports.', 'url': '#', 'permission': 'gst_reports', 'icon': '📊'},
    ]
    cards = [c for c in cards if has_permission(c['permission'])]
    return render_template(
        'portal/module_hub.html',
        module_title='GST / Audit',
        module_kicker='Future Module',
        module_description='GST dashboard, invoice upload, audit checks and reports will be grouped here.',
        cards=cards,
        back_url=url_for('portal_workspace'),
        notice='GST / Audit module is not integrated yet.',
    )


@app.route('/portal/reports')
@login_required
@permission_required('reports_view')
def portal_reports():
    cards = [
        {'title': 'Business Reports', 'description': 'Business overview and project reports.', 'url': '#', 'permission': 'reports_view', 'icon': '📈'},
        {'title': 'Stock Reports', 'description': 'Stock reports will connect after stock integration.', 'url': '#', 'permission': 'stock_reports', 'icon': '📦'},
        {'title': 'Employee Reports', 'description': 'Employee reports will connect after employee integration.', 'url': '#', 'permission': 'reports_view', 'icon': '👥'},
        {'title': 'Access Reports', 'description': 'User access and permission overview.', 'url': '/portal/users', 'permission': 'users_view', 'icon': '🔐'},
    ]
    cards = [c for c in cards if has_permission(c['permission'])]
    return render_template(
        'portal/module_hub.html',
        module_title='Reports',
        module_kicker='Reports Hub',
        module_description='Business, stock, project, employee and access reports are grouped here.',
        cards=cards,
        back_url=url_for('portal_workspace'),
        notice='Some report cards are placeholders until their modules are integrated.',
    )


@app.route('/portal/users')
@login_required
@permission_required('users_view')
def portal_users():
    cards = [
        {'title': 'Users & Roles', 'description': 'Create users, assign roles, reset passwords and disable accounts.', 'url': '/admin/users?module=users', 'permission': 'users_view', 'icon': '👤'},
        {'title': 'Role Permissions', 'description': 'Choose what Company Owner, Manager, Supervisor, Authorized Person and Viewer can see/change.', 'url': '/admin/permissions?module=users', 'permission': 'roles_manage', 'icon': '🔐'},
        {'title': 'User Access Summary', 'description': 'Review who can access Website, Stock, Employees, GST, Reports, Users and System.', 'url': '/admin/users?module=users', 'permission': 'users_view', 'icon': '📋'},
        {'title': 'Audit / Access Logs', 'description': 'Access-log page placeholder until audit log UI is separated.', 'url': '/portal/system', 'permission': 'audit_view', 'icon': '🧭'},
    ]
    cards = [c for c in cards if has_permission(c['permission'])]
    return render_template(
        'portal/module_hub.html',
        module_title='Users & Access Control',
        module_kicker='Portal Module',
        module_description='Manage people, roles and permissions separately from website editing. User creation and role permission editing are different jobs.',
        cards=cards,
        back_url=url_for('portal_workspace'),
    )


@app.route('/portal/system')
@login_required
@permission_required('system_settings')
def portal_system():
    cards = [
        {'title': 'Admin Dashboard', 'description': 'Production status and content warnings.', 'url': '/admin?module=system', 'permission': 'system_settings', 'icon': '📊'},
        {'title': 'Download Backup', 'description': 'Download website content backup.', 'url': '/admin/backup?module=system', 'permission': 'backup_download', 'icon': '💾'},
        {'title': 'Restore Backup', 'description': 'Restore JSON backups carefully.', 'url': '/admin/restore?module=system', 'permission': 'backup_restore', 'icon': '♻️'},
        {'title': 'Version History', 'description': 'Review old content versions.', 'url': '/admin/versions?module=system', 'permission': 'audit_view', 'icon': '🕒'},
    ]
    cards = [c for c in cards if has_permission(c['permission'])]
    return render_template(
        'portal/module_hub.html',
        module_title='System Control',
        module_kicker='Protected Module',
        module_description='System status, backups, restore, version history and audit-related controls.',
        cards=cards,
        back_url=url_for('portal_workspace'),
    )
