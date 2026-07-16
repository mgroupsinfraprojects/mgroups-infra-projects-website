(() => {
  'use strict';

  const body = document.body;
  const openButton = document.querySelector('[data-sidebar-open]');
  const closeButtons = document.querySelectorAll('[data-sidebar-close]');

  openButton?.addEventListener('click', () => body.classList.add('sidebar-open'));
  closeButtons.forEach((button) => button.addEventListener('click', () => body.classList.remove('sidebar-open')));
  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape') body.classList.remove('sidebar-open');
  });

  document.querySelectorAll('[data-confirm]').forEach((form) => {
    form.addEventListener('submit', (event) => {
      const message = form.dataset.confirm || 'Continue with this action?';
      if (!window.confirm(message)) event.preventDefault();
    });
  });

  const payType = document.querySelector('#pay_type');
  const dailyGroup = document.querySelector('[data-pay-group="daily"]');
  const monthlyGroup = document.querySelector('[data-pay-group="monthly"]');
  const syncPayFields = () => {
    if (!payType || !dailyGroup || !monthlyGroup) return;
    const isDaily = payType.value === 'Daily';
    dailyGroup.classList.toggle('opacity-50', !isDaily);
    monthlyGroup.classList.toggle('opacity-50', isDaily);
    dailyGroup.querySelector('input')?.toggleAttribute('required', isDaily);
    monthlyGroup.querySelector('input')?.toggleAttribute('required', !isDaily);
  };
  payType?.addEventListener('change', syncPayFields);
  syncPayFields();

  document.querySelectorAll('[data-bulk-status]').forEach((button) => {
    button.addEventListener('click', () => {
      const status = button.dataset.bulkStatus;
      document.querySelectorAll('[data-attendance-status]').forEach((select) => {
        select.value = status;
        select.dispatchEvent(new Event('change'));
      });
    });
  });

  const attendanceForm = document.querySelector('[data-attendance-form]');
  const updateAttendanceCounter = () => {
    if (!attendanceForm) return;
    const statuses = [...attendanceForm.querySelectorAll('[data-attendance-status]')];
    const present = statuses.filter((item) => ['Present', 'Half Day'].includes(item.value)).length;
    const absent = statuses.filter((item) => item.value === 'Absent').length;
    document.querySelector('[data-present-count]')?.replaceChildren(document.createTextNode(String(present)));
    document.querySelector('[data-absent-count]')?.replaceChildren(document.createTextNode(String(absent)));
  };
  attendanceForm?.querySelectorAll('[data-attendance-status]').forEach((select) => select.addEventListener('change', updateAttendanceCounter));
  updateAttendanceCounter();

  document.querySelectorAll('.app-alert').forEach((alert, index) => {
    window.setTimeout(() => {
      if (document.body.contains(alert)) bootstrap.Alert.getOrCreateInstance(alert).close();
    }, 6500 + (index * 500));
  });
})();
