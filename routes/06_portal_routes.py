# M-GROUPS Portal / My Workspace routes. Executed by app.py in application globals.

@app.route('/portal')
@login_required
def portal_workspace():
    modules = allowed_modules()
    return render_template('portal/workspace.html', modules=modules, user=current_admin(), role_label=role_label)


@app.route('/portal/web')
@login_required
@permission_required('website_view')
def portal_web():
    # Keep the existing website admin system as the Website module for now.
    return redirect(url_for('admin_dashboard'))


@app.route('/portal/stock')
@login_required
@permission_required('stock_view')
def portal_stock():
    return render_template(
        'portal/module_placeholder.html',
        module_title='Stock Management',
        module_key='stock',
        module_description='Materials, store stock, site stock, transfers, issues and stock reports will open here after the stock app is converted into a protected portal module.',
        quick_actions=['View stock dashboard', 'Stock in / receive', 'Transfer material', 'Site stock reports'],
        status='Pending integration from your stock management ZIP.'
    )


@app.route('/portal/employees')
@login_required
@permission_required('employees_view')
def portal_employees():
    return render_template(
        'portal/module_placeholder.html',
        module_title='Employee Management',
        module_key='employees',
        module_description='Employee records, attendance, supervisor assignment, work records and employee reports will be added here.',
        quick_actions=['Employee list', 'Attendance', 'Work records', 'Employee reports'],
        status='Future module placeholder.'
    )


@app.route('/portal/gst')
@login_required
@permission_required('gst_view')
def portal_gst():
    return render_template(
        'portal/module_placeholder.html',
        module_title='GST / Audit',
        module_key='gst',
        module_description='GST dashboards, invoice upload, audit checks and GST reports will open here after the GST tool is integrated.',
        quick_actions=['GST dashboard', 'Invoice upload', 'Audit checks', 'GST reports'],
        status='Future module placeholder.'
    )


@app.route('/portal/reports')
@login_required
@permission_required('reports_view')
def portal_reports():
    return render_template(
        'portal/module_placeholder.html',
        module_title='Reports',
        module_key='reports',
        module_description='Business, stock, project, employee and access reports will be grouped here.',
        quick_actions=['Business reports', 'Stock reports', 'Project reports', 'Access reports'],
        status='Reports hub placeholder.'
    )


@app.route('/portal/users')
@login_required
@permission_required('users_view')
def portal_users():
    return redirect(url_for('admin_users'))


@app.route('/portal/system')
@login_required
@permission_required('system_settings')
def portal_system():
    return render_template(
        'portal/module_placeholder.html',
        module_title='System Control',
        module_key='system',
        module_description='System status, backup, restore, version history and audit logs are available only to developer/full-control users.',
        quick_actions=['Production status', 'Download backup', 'Version history', 'Restore backup'],
        status='System tools are protected. Use current admin pages until the system hub is fully built.'
    )
