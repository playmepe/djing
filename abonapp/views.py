# -*- coding: utf-8 -*-
from json import dumps
from django.contrib.gis.shortcuts import render_to_text
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, ProgrammingError
from django.db.models import Count, Q
from django.db.transaction import atomic
from django.shortcuts import render, redirect, get_object_or_404, resolve_url
from django.contrib.auth.decorators import login_required, permission_required
from django.utils import timezone
from django.http import HttpResponse
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _

from statistics.models import StatCache
from tariff_app.models import Tariff
from agent import NasFailedResult, Transmitter, NasNetworkError
from . import forms
from . import models
import mydefs
from devapp.models import Device, Port as DevPort
from datetime import datetime, date
from taskapp.models import Task
from dialing_app.models import AsteriskCDR
from statistics.models import getModel, get_dates


@login_required
@mydefs.only_admins
def peoples(request, gid):
    street_id = mydefs.safe_int(request.GET.get('street'))
    peoples_list = models.Abon.objects.select_related('group', 'street')
    if street_id > 0:
        peoples_list = peoples_list.filter(group=gid, street=street_id)
    else:
        peoples_list = peoples_list.filter(group=gid)

    # фильтр
    dr, field = mydefs.order_helper(request)
    if field:
        peoples_list = peoples_list.order_by(field)

    try:
        peoples_list = mydefs.pag_mn(request, peoples_list)
        for abon in peoples_list:
            if abon.ip_address is not None:
                try:
                    abon.stat_cache = StatCache.objects.get(ip=abon.ip_address)
                except StatCache.DoesNotExist:
                    pass

    except mydefs.LogicError as e:
        messages.warning(request, e)

    streets = models.AbonStreet.objects.filter(group=gid)

    return render(request, 'abonapp/peoples.html', {
        'peoples': peoples_list,
        'abon_group': get_object_or_404(models.AbonGroup, pk=gid),
        'streets': streets,
        'street_id': street_id,
        'dir': dr,
        'order_by': request.GET.get('order_by')
    })


@login_required
@permission_required('abonapp.add_abongroup')
def addgroup(request):
    frm = forms.AbonGroupForm()
    try:
        if request.method == 'POST':
            frm = forms.AbonGroupForm(request.POST)
            if frm.is_valid():
                frm.save()
                messages.success(request, _('create group success msg'))
                return redirect('abonapp:group_list')
            else:
                messages.error(request, _('fix form errors'))
    except (NasFailedResult, NasNetworkError) as e:
        messages.error(request, e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    return render(request, 'abonapp/addGroup.html', {
        'form': frm
    })


@login_required
@mydefs.only_admins
def grouplist(request):
    groups = models.AbonGroup.objects.annotate(usercount=Count('abon')).order_by('title')

    # фильтр
    directory, field = mydefs.order_helper(request)
    if field:
        groups = groups.order_by(field)

    groups = mydefs.pag_mn(request, groups)

    return render(request, 'abonapp/group_list.html', {
        'groups': groups,
        'dir': directory,
        'order_by': request.GET.get('order_by')
    })


@login_required
@permission_required('abonapp.delete_abongroup')
def delgroup(request):
    try:
        agd = mydefs.safe_int(request.GET.get('id'))
        get_object_or_404(models.AbonGroup, pk=agd).delete()
        messages.success(request, _('delete group success msg'))
        return mydefs.res_success(request, 'abonapp:group_list')
    except (NasFailedResult, NasNetworkError) as e:
        messages.error(request, e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    return mydefs.res_error(request, 'abonapp:group_list')


@login_required
@permission_required('abonapp.add_abon')
def addabon(request, gid):
    frm = None
    group = None
    try:
        group = get_object_or_404(models.AbonGroup, pk=gid)
        if request.method == 'POST':
            frm = forms.AbonForm(request.POST, initial={'group': group})
            if frm.is_valid():
                abon = frm.save()
                messages.success(request, _('create abon success msg'))
                return redirect('abonapp:abon_home', group.id, abon.pk)
            else:
                messages.error(request, _('fix form errors'))

    except (IntegrityError, NasFailedResult, NasNetworkError, mydefs.LogicError) as e:
        messages.error(request, e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)

    if not frm:
        frm = forms.AbonForm(initial={
            'group': group,
            'address': _('Address'),
            'is_active': False
        })

    return render(request, 'abonapp/addAbon.html', {
        'form': frm,
        'abon_group': group
    })


@login_required
@mydefs.only_admins
def delentity(request):
    typ = request.GET.get('t')
    uid = request.GET.get('id')
    try:
        if typ == 'a':
            if not request.user.has_perm('abonapp.delete_abon'):
                raise PermissionDenied
            abon = get_object_or_404(models.Abon, pk=uid)
            gid = abon.group.id
            abon.delete()
            messages.success(request, _('delete abon success msg'))
            return mydefs.res_success(request, resolve_url('abonapp:people_list', gid=gid))
        elif typ == 'g':
            if not request.user.has_perm('abonapp.delete_abongroup'):
                raise PermissionDenied
            get_object_or_404(models.AbonGroup, pk=uid).delete()
            messages.success(request, _('delete group success msg'))
            return mydefs.res_success(request, 'abonapp:group_list')
        else:
            messages.warning(request, _('I not know what to delete'))
    except NasNetworkError as e:
        messages.error(request, e)
    except NasFailedResult as e:
        messages.error(request, _("NAS says: '%s'") % e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    return redirect('abonapp:group_list')


@login_required
@permission_required('abonapp.can_add_ballance')
@atomic
def abonamount(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    try:
        if request.method == 'POST':
            abonid = mydefs.safe_int(request.POST.get('abonid'))
            if abonid == int(uid):
                amnt = mydefs.safe_float(request.POST.get('amount'))
                abon.add_ballance(request.user, amnt, comment=_('fill account through admin side'))
                abon.save(update_fields=['ballance'])
                messages.success(request, _('Account filled successfully on %.2f') % amnt)
                return redirect('abonapp:abon_phistory', gid=gid, uid=uid)
            else:
                messages.error(request, _('I not know the account id'))
    except (NasNetworkError, NasFailedResult) as e:
        messages.error(request, e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    return render_to_text('abonapp/modal_abonamount.html', {
        'abon': abon,
        'abon_group': get_object_or_404(models.AbonGroup, pk=gid)
    }, request=request)


@login_required
@mydefs.only_admins
def invoice_for_payment(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    invoices = models.InvoiceForPayment.objects.filter(abon=abon)
    invoices = mydefs.pag_mn(request, invoices)
    return render(request, 'abonapp/invoiceForPayment.html', {
        'invoices': invoices,
        'abon_group': abon.group,
        'abon': abon
    })


@login_required
@mydefs.only_admins
def pay_history(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    pay_history = models.AbonLog.objects.filter(abon=abon).order_by('-id')
    pay_history = mydefs.pag_mn(request, pay_history)
    return render(request, 'abonapp/payHistory.html', {
        'pay_history': pay_history,
        'abon_group': abon.group,
        'abon': abon
    })


@login_required
@mydefs.only_admins
def abon_services(request, gid, uid):
    grp = get_object_or_404(models.AbonGroup, pk=gid)
    abon = get_object_or_404(models.Abon, pk=uid)

    return render(request, 'abonapp/service.html', {
        'abon': abon,
        'abon_tariff': abon.current_tariff,
        'abon_group': abon.group,
        'services': grp.tariffs.all()
    })


@login_required
@mydefs.only_admins
def abonhome(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    abon_group = get_object_or_404(models.AbonGroup, pk=gid)
    frm = None
    passw = None
    try:
        if request.method == 'POST':
            if not request.user.has_perm('abonapp.change_abon'):
                raise PermissionDenied
            frm = forms.AbonForm(request.POST, instance=abon)
            if frm.is_valid():
                abon.ip_address = request.POST.get('ip')
                frm.save()
                messages.success(request, _('edit abon success msg'))
            else:
                messages.warning(request, _('fix form errors'))
        else:
            passw = models.AbonRawPassword.objects.get(account=abon).passw_text
            frm = forms.AbonForm(instance=abon, initial={'password': passw})
            if abon.device is None:
                messages.warning(request, _('User device was not found'))
    except mydefs.LogicError as e:
        messages.error(request, e)
        passw = models.AbonRawPassword.objects.get(account=abon).passw_text
        frm = forms.AbonForm(instance=abon, initial={'password': passw})

    except (NasFailedResult, NasNetworkError) as e:
        messages.error(request, e)
    except models.AbonRawPassword.DoesNotExist:
        messages.warning(request, _('User has not have password, and cannot login'))
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)

    if request.user.has_perm('abonapp.change_abon'):
        return render(request, 'abonapp/editAbon.html', {
            'form': frm or forms.AbonForm(instance=abon, initial={'password': passw}),
            'abon': abon,
            'abon_group': abon_group,
            'ip': abon.ip_address,
            'is_bad_ip': getattr(abon, 'is_bad_ip', False),
            'device': abon.device,
            'dev_ports': DevPort.objects.filter(device=abon.device) if abon.device else None
        })
    else:
        return render(request, 'abonapp/viewAbon.html', {
            'abon': abon,
            'abon_group': abon_group,
            'ip': abon.ip_address,
            'passw': passw
        })


@atomic
def terminal_pay(request):
    from .pay_systems import allpay
    ret_text = allpay(request)
    return HttpResponse(ret_text)


@login_required
@permission_required('abonapp.add_invoiceforpayment')
def add_invoice(request, gid, uid):
    uid = mydefs.safe_int(uid)
    abon = get_object_or_404(models.Abon, pk=uid)
    grp = get_object_or_404(models.AbonGroup, pk=gid)

    try:
        if request.method == 'POST':
            curr_amount = mydefs.safe_int(request.POST.get('curr_amount'))
            comment = request.POST.get('comment')

            newinv = models.InvoiceForPayment()
            newinv.abon = abon
            newinv.amount = curr_amount
            newinv.comment = comment

            if request.POST.get('status') == 'on':
                newinv.status = True

            newinv.author = request.user
            newinv.save()
            messages.success(request, _('Receipt has been created'))
            return redirect('abonapp:abon_home', gid=gid, uid=uid)

    except (NasNetworkError, NasFailedResult) as e:
        messages.error(request, e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    return render(request, 'abonapp/addInvoice.html', {
        'abon': abon,
        'invcount': models.InvoiceForPayment.objects.filter(abon=abon).count(),
        'abon_group': grp
    })


@login_required
@permission_required('abonapp.can_buy_tariff')
@atomic
def pick_tariff(request, gid, uid):
    grp = get_object_or_404(models.AbonGroup, pk=gid)
    abon = get_object_or_404(models.Abon, pk=uid)
    tariffs = grp.tariffs.all()
    try:
        if request.method == 'POST':
            trf = Tariff.objects.get(pk=request.POST.get('tariff'))
            deadline = request.POST.get('deadline')
            if deadline == '' or deadline is None:
                abon.pick_tariff(trf, request.user)
            else:
                deadline = datetime.strptime(deadline, '%Y-%m-%d')
                abon.pick_tariff(trf, request.user, deadline=deadline)
            messages.success(request, _('Tariff has been picked'))
            return redirect('abonapp:abon_services', gid=gid, uid=abon.id)
    except (mydefs.LogicError, NasFailedResult) as e:
        messages.error(request, e)
    except NasNetworkError as e:
        messages.error(request, e)
        return redirect('abonapp:abon_services', gid=gid, uid=abon.id)
    except Tariff.DoesNotExist:
        messages.error(request, _('Tariff your picked does not exist'))
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    except ValueError as e:
        messages.error(request, "%s: %s" % (_('fix form errors'), e))

    return render(request, 'abonapp/buy_tariff.html', {
        'tariffs': tariffs,
        'abon': abon,
        'abon_group': grp,
        'selected_tariff': mydefs.safe_int(request.GET.get('selected_tariff'))
    })


@login_required
@permission_required('abonapp.can_complete_service')
@atomic
def complete_service(request, gid, uid, srvid):
    abtar = get_object_or_404(models.AbonTariff, pk=srvid)
    abon = abtar.abon
    # считаем не использованные ресурсы
    calc_obj = abtar.tariff.get_calc_type()(abtar)
    # получаем сколько использовано
    res_amount = calc_obj.calc_amount()
    cashback = abtar.tariff.amount - res_amount

    if abtar.abon.group is None:
        abon.group = get_object_or_404(models.AbonGroup, pk=gid)
        abon.save(update_fields=['group'])
    if int(abtar.abon.pk) != int(uid) or int(abtar.abon.group.pk) != int(gid):
        # если что-то написали в урле вручную, то вернём на путь истинный
        return redirect('abonapp:compl_srv', gid=abtar.abon.group.pk, uid=abtar.abon.pk, srvid=srvid)
    time_use = None
    try:
        if request.method == 'POST':
            # досрочно завершаем услугу
            if request.POST.get('finish_confirm') == 'yes':
                if cashback > 0.5:
                    # возвращаем деньги, которые абонент не использовал
                    abon.add_ballance(
                        request.user,
                        cashback,
                        _('Refunds for unused resources')
                    )
                    abon.save(update_fields=['ballance'])

                # удаляем запись о текущей услуге.
                abtar.delete()
                messages.success(request, _('Service has been finished successfully'))
                return redirect('abonapp:abon_services', gid, uid)
            else:
                raise mydefs.LogicError(_('Not confirmed'))

        time_use = mydefs.RuTimedelta(timezone.now() - abtar.time_start)

    except (mydefs.LogicError, NasFailedResult) as e:
        messages.error(request, e)
    except NasNetworkError as e:
        messages.warning(request, e)
        return redirect('abonapp:abon_home', gid, uid)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)

    return render(request, 'abonapp/complete_service.html', {
        'abtar': abtar,
        'abon': abon,
        'time_use': time_use,
        'abon_group': get_object_or_404(models.AbonGroup, pk=gid),
        'tcost': round(res_amount, 4),
        'cashback': round(cashback, 4)
    })


@login_required
@permission_required('abonapp.delete_abontariff')
def unsubscribe_service(request, gid, uid, abon_tariff_id):
    try:
        get_object_or_404(models.AbonTariff, pk=int(abon_tariff_id)).delete()
        messages.success(request, _('User has been detached from service'))
    except NasFailedResult as e:
        messages.error(request, e)
    except NasNetworkError as e:
        messages.warning(request, e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    return redirect('abonapp:abon_services', gid=gid, uid=uid)


@login_required
@mydefs.only_admins
def log_page(request):
    logs = models.AbonLog.objects.all()
    logs = mydefs.pag_mn(request, logs)
    return render(request, 'abonapp/log.html', {
        'logs': logs
    })


@login_required
@mydefs.only_admins
def debtors(request):
    # peoples_list = models.Abon.objects.filter(invoiceforpayment__status=True)
    # peoples_list = mydefs.pag_mn(request, peoples_list)
    invs = models.InvoiceForPayment.objects.filter(status=True)
    invs = mydefs.pag_mn(request, invs)
    return render(request, 'abonapp/debtors.html', {
        # 'peoples': peoples_list
        'invoices': invs
    })


@login_required
@mydefs.only_admins
def update_nas(request, group_id):
    users = models.Abon.objects.filter(group=group_id)
    try:
        tm = Transmitter()
        for usr in users:
            if not usr.ip_address:
                continue
            agent_abon = usr.build_agent_struct()
            if agent_abon is not None:
                tm.update_user(agent_abon)
    except NasFailedResult as e:
        messages.error(request, e)
    except NasNetworkError as e:
        messages.warning(request, e)
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
    return redirect('abonapp:people_list', gid=group_id)


@login_required
@mydefs.only_admins
def task_log(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    tasks = Task.objects.filter(abon=abon)
    return render(request, 'abonapp/task_log.html', {
        'tasks': tasks,
        'abon_group': get_object_or_404(models.AbonGroup, pk=gid),
        'abon': abon
    })


@login_required
@mydefs.only_admins
def passport_view(request, gid, uid):
    try:
        abon = models.Abon.objects.get(pk=uid)
        if request.method == 'POST':
            try:
                passport_instance = models.PassportInfo.objects.get(abon=abon)
            except models.PassportInfo.DoesNotExist:
                passport_instance = None
            frm = forms.PassportForm(request.POST, instance=passport_instance)
            if frm.is_valid():
                pi = frm.save(commit=False)
                pi.abon = abon
                pi.save()
                messages.success(request, _('Passport information has been saved'))
                return redirect('abonapp:passport_view', gid=gid, uid=uid)
            else:
                messages.error(request, _('fix form errors'))
        else:
            passp_instance = models.PassportInfo.objects.get(abon=abon)
            frm = forms.PassportForm(instance=passp_instance)
    except models.Abon.DoesNotExist:
        messages.error(request, _('Abon does not exist'))
        return redirect('abonapp:people_list', gid=gid)
    except models.PassportInfo.DoesNotExist:
        messages.warning(request, _('Passport info for the user does not exist'))
        frm = forms.PassportForm()
    return render(request, 'abonapp/passport_view.html', {
        'abon_group': get_object_or_404(models.AbonGroup, pk=gid),
        'abon': abon,
        'frm': frm
    })


@login_required
@mydefs.only_admins
def chgroup_tariff(request, gid):
    grp = get_object_or_404(models.AbonGroup, pk=gid)
    if request.method == 'POST':
        tr = request.POST.getlist('tr')
        grp.tariffs.clear()
        grp.tariffs.add(*[int(d) for d in tr])
        grp.save()
    tariffs = Tariff.objects.all()
    return render(request, 'abonapp/group_tariffs.html', {
        'abon_group': grp,
        'tariffs': tariffs
    })


@login_required
@mydefs.only_admins
def dev(request, gid, uid):
    abon_dev = None
    try:
        abon = models.Abon.objects.get(pk=uid)
        if request.method == 'POST':
            dev = Device.objects.get(pk=request.POST.get('dev'))
            abon.device = dev
            abon.save(update_fields=['device'])
            messages.success(request, _('Device has successfully attached'))
            return redirect('abonapp:abon_home', gid=gid, uid=uid)
        else:
            abon_dev = abon.device
    except Device.DoesNotExist:
        messages.warning(request, _('Device your selected already does not exist'))
    except models.Abon.DoesNotExist:
        messages.error(request, _('Abon does not exist'))
        return redirect('abonapp:people_list', gid=gid)
    return render(request, 'abonapp/modal_dev.html', {
        'devices': Device.objects.filter(user_group=gid),
        'dev': abon_dev,
        'gid': gid, 'uid': uid
    })


@login_required
@mydefs.only_admins
def clear_dev(request, gid, uid):
    try:
        abon = models.Abon.objects.get(pk=uid)
        abon.device = None
        abon.save(update_fields=['device'])
        messages.success(request, _('Device has successfully unattached'))
    except models.Abon.DoesNotExist:
        messages.error(request, _('Abon does not exist'))
        return redirect('abonapp:people_list', gid=gid)
    return redirect('abonapp:abon_home', gid=gid, uid=uid)


@login_required
@mydefs.only_admins
def charts(request, gid, uid):
    high = 100

    wandate = request.GET.get('wantdate')
    if wandate:
        wandate = datetime.strptime(wandate, '%d%m%Y').date()
    else:
        wandate = date.today()

    try:
        StatElem = getModel(wandate)
        abon = models.Abon.objects.get(pk=uid)
        if abon.group is None:
            abon.group = models.AbonGroup.objects.get(pk=gid)
            abon.save(update_fields=['group'])
        abongroup = abon.group

        if abon.ip_address is None:
            charts_data = None
        else:
            charts_data = StatElem.objects.chart(
                abon.ip_address,
                count_of_parts=30,
                want_date=wandate
            )

            abontariff = abon.active_tariff()
            if abontariff is not None:
                trf = abontariff.tariff
                high = trf.speedIn + trf.speedOut
                if high > 100:
                    high = 100

    except models.Abon.DoesNotExist:
        messages.error(request, _('Abon does not exist'))
        return redirect('abonapp:people_list', gid)
    except models.AbonGroup.DoesNotExist:
        messages.error(request, _("Group what you want doesn't exist"))
        return redirect('abonapp:group_list')
    except ProgrammingError as e:
        messages.error(request, e)
        return redirect('abonapp:abon_home', gid=gid, uid=uid)

    return render(request, 'abonapp/charts.html', {
        'abon_group': abongroup,
        'abon': abon,
        'charts_data': ',\n'.join(charts_data) if charts_data is not None else None,
        'high': high,
        'dates': get_dates()
    })


@login_required
@permission_required('abonapp.add_extra_fields_model')
def make_extra_field(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    try:
        if request.method == 'POST':
            frm = forms.ExtraFieldForm(request.POST)
            if frm.is_valid():
                field_instance = frm.save()
                abon.extra_fields.add(field_instance)
                messages.success(request, _('Extra field successfully created'))
            else:
                messages.error(request, _('fix form errors'))
            return redirect('abonapp:abon_home', gid=gid, uid=uid)
        else:
            frm = forms.ExtraFieldForm()

    except (NasNetworkError, NasFailedResult) as e:
        messages.error(request, e)
        frm = forms.ExtraFieldForm()
    except mydefs.MultipleException as errs:
        for err in errs.err_list:
            messages.add_message(request, messages.constants.ERROR, err)
        frm = forms.ExtraFieldForm()
    return render_to_text('abonapp/modal_extra_field.html', {
        'abon': abon,
        'gid': gid,
        'frm': frm
    }, request=request)


@login_required
@permission_required('abonapp.change_extra_fields_model')
def extra_field_change(request, gid, uid):
    extras = [(int(x), y) for x, y in zip(request.POST.getlist('ed'), request.POST.getlist('ex'))]
    try:
        for ex in extras:
            extra_field = models.ExtraFieldsModel.objects.get(pk=ex[0])
            extra_field.data = ex[1]
            extra_field.save(update_fields=['data'])
        messages.success(request, _("Extra fields has been saved"))
    except models.ExtraFieldsModel.DoesNotExist:
        messages.error(request, _('One or more extra fields has not been saved'))
    return redirect('abonapp:abon_home', gid=gid, uid=uid)


@login_required
@permission_required('abonapp.delete_extra_fields_model')
def extra_field_delete(request, gid, uid, fid):
    abon = get_object_or_404(models.Abon, pk=uid)
    try:
        extra_field = models.ExtraFieldsModel.objects.get(pk=fid)
        abon.extra_fields.remove(extra_field)
        extra_field.delete()
        messages.success(request, _('Extra field successfully deleted'))
    except models.ExtraFieldsModel.DoesNotExist:
        messages.warning(request, _('Extra field does not exist'))
    return redirect('abonapp:abon_home', gid=gid, uid=uid)


@login_required
def abon_ping(request):
    ip = request.GET.get('cmd_param')
    status = False
    text = '<span class="glyphicon glyphicon-exclamation-sign"></span> %s' % _('no ping')
    try:
        if ip is None:
            raise mydefs.LogicError(_('Ip not passed'))
        tm = Transmitter()
        ping_result = tm.ping(ip)
        if ping_result is None:
            if mydefs.ping(ip, 10):
                status = True
                text = '<span class="glyphicon glyphicon-ok"></span> %s' % _('ping ok')
        else:
            if type(ping_result) is tuple:
                loses_percent = (ping_result[0] / ping_result[1] if ping_result[1] != 0 else 1)
                if loses_percent > 0.5:
                    text = '<span class="glyphicon glyphicon-ok"></span> %s' % _('ok ping, %d/%d loses') % ping_result
                    status = True
                else:
                    text = '<span class="glyphicon glyphicon-exclamation-sign"></span> %s' % _('no ping, %d/%d loses') % ping_result
            else:
                text = '<span class="glyphicon glyphicon-ok"></span> %s' % _('ping ok') + ' ' + str(ping_result)
                status = True

    except (NasFailedResult, mydefs.LogicError) as e:
        messages.error(request, e)
    except NasNetworkError as e:
        messages.warning(request, e)

    return HttpResponse(dumps({
        'status': 0 if status else 1,
        'dat': text
    }))


@login_required
@mydefs.only_admins
def dials(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    if hasattr(abon.group, 'pk') and abon.group.pk != int(gid):
        return redirect('abonapp:dials', abon.group.pk, abon.pk)
    if abon.telephone is not None and abon.telephone != '':
        tel = abon.telephone.replace('+', '')
        logs = AsteriskCDR.objects.filter(
            Q(src__contains=tel) | Q(dst__contains=tel)
        )
        logs = mydefs.pag_mn(request, logs)
    else:
        logs = None
    return render(request, 'abonapp/dial_log.html', {
        'logs': logs,
        'abon_group': get_object_or_404(models.AbonGroup, pk=gid),
        'abon': abon
    })


@login_required
@mydefs.only_admins
def save_user_dev_port(request, gid, uid):
    if request.method != 'POST':
        messages.error(request, _('Method is not POST'))
        return redirect('abonapp:abon_home', gid, uid)
    user_port = mydefs.safe_int(request.POST.get('user_port'))
    is_dynamic_ip = request.POST.get('is_dynamic_ip')
    try:
        if user_port == 0:
            port = None
        else:
            port = DevPort.objects.get(pk=user_port)
        abon = models.Abon.objects.get(pk=uid)
        abon.dev_port = port
        if abon.is_dynamic_ip != is_dynamic_ip:
            abon.is_dynamic_ip = is_dynamic_ip
            abon.save(update_fields=['dev_port', 'is_dynamic_ip'])
        else:
            abon.save(update_fields=['dev_port'])
        messages.success(request, _('User port has been saved'))
    except DevPort.DoesNotExist:
        messages.error(request, _('Selected port does not exist'))
    except models.Abon.DoesNotExist:
        messages.error(request, _('User does not exist'))
    return redirect('abonapp:abon_home', gid, uid)


@login_required
@permission_required('abonapp.add_abonstreet')
def street_add(request, gid):
    if request.method == 'POST':
        frm = forms.AbonStreetForm(request.POST)
        if frm.is_valid():
            frm.save()
            messages.success(request, _('Street successfully saved'))
            return redirect('abonapp:people_list', gid)
        else:
            messages.error(request, _('fix form errors'))
    else:
        frm = forms.AbonStreetForm(initial={'group': gid})
    return render_to_text('abonapp/modal_addstreet.html', {
        'form': frm,
        'gid': gid
    }, request=request)


@login_required
@permission_required('abonapp.change_abonstreet')
def street_edit(request, gid):
    try:
        if request.method == 'POST':
            streets_pairs = [(int(sid), sname) for sid, sname in zip(request.POST.getlist('sid'), request.POST.getlist('sname'))]
            for sid, sname in streets_pairs:
                street = models.AbonStreet.objects.get(pk=sid)
                street.name = sname
                street.save()
            messages.success(request, _('Streets has been saved'))
        else:
            return render_to_text('abonapp/modal_editstreet.html', {
                'gid': gid,
                'streets': models.AbonStreet.objects.filter(group=gid)
            }, request=request)

    except models.AbonStreet.DoesNotExist:
        messages.error(request, _('One of these streets has not been found'))

    return redirect('abonapp:people_list', gid)


@login_required
@permission_required('abonapp.delete_abonstreet')
def street_del(request, gid, sid):
    try:
        models.AbonStreet.objects.get(pk=sid, group=gid).delete()
        messages.success(request, _('The street successfully deleted'))
    except models.AbonStreet.DoesNotExist:
        messages.error(request, _('The street has not been found'))
    return redirect('abonapp:people_list', gid)


@login_required
@mydefs.only_admins
def tels(request, gid, uid):
    abon = get_object_or_404(models.Abon, pk=uid)
    telephones = abon.additional_telephones.all()
    return render_to_text('abonapp/modal_additional_telephones.html', {
        'telephones': telephones,
        'gid': gid,
        'uid': uid
    }, request=request)


@login_required
@permission_required('abnapp.add_additionaltelephone')
def tel_add(request, gid, uid):
    if request.method == 'POST':
        frm = forms.AdditionalTelephoneForm(request.POST)
        if frm.is_valid():
            new_tel = frm.save(commit=False)
            abon = get_object_or_404(models.Abon, pk=uid)
            new_tel.abon = abon
            new_tel.save()
            messages.success(request, _('New telephone has been saved'))
            return redirect('abonapp:abon_home', gid, uid)
        else:
            messages.error(request, _('fix form errors'))
    else:
        frm = forms.AdditionalTelephoneForm()
    return render_to_text('abonapp/modal_add_phone.html', {
        'form': frm,
        'gid': gid,
        'uid': uid
    }, request=request)


@login_required
@permission_required('abnapp.delete_additionaltelephone')
def tel_del(request, gid, uid):
    try:
        tid = mydefs.safe_int(request.GET.get('tid'))
        tel = models.AdditionalTelephone.objects.get(pk=tid)
        tel.delete()
        messages.success(request, _('Additional telephone successfully deleted'))
    except models.AdditionalTelephone.DoesNotExist:
        messages.error(request, _('Telephone not found'))
    return redirect('abonapp:abon_home', gid, uid)


# API's

def abons(request):
    ablist = [{
        'id': abn.pk,
        'tarif_id': abn.active_tariff().tariff.pk if abn.active_tariff() is not None else 0,
        'ip': abn.ip_address.int_ip(),
        'is_active': abn.is_active
    } for abn in models.Abon.objects.all()]

    tarlist = [{
        'id': trf.pk,
        'speedIn': trf.speedIn,
        'speedOut': trf.speedOut
    } for trf in Tariff.objects.all()]

    data = {
        'subscribers': ablist,
        'tariffs': tarlist
    }
    del ablist, tarlist
    return HttpResponse(dumps(data))


def search_abon(request):
    word = request.GET.get('s')
    results = models.Abon.objects.filter(fio__icontains=word)[:8]
    results = [{'id': usr.pk, 'text': "%s: %s" % (usr.username, usr.fio)} for usr in results]
    return HttpResponse(dumps(results, ensure_ascii=False))
