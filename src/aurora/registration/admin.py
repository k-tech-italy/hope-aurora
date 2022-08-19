import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import pytz
from django.core.cache import cache

from admin_extra_buttons.decorators import button, link, view
from adminfilters.autocomplete import AutoCompleteFilter
from adminfilters.value import ValueFilter
from dateutil.utils import today
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.admin import SimpleListFilter, register
from django.db.models import JSONField
from django.db.models.signals import post_delete, post_save
from django.db.transaction import atomic
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.urls import reverse, translate_url
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext as _
from jsoneditor.forms import JSONEditor
from smart_admin.modeladmin import SmartModelAdmin
from ..core.admin import ConcurrencyVersionAdmin

from ..core.models import FormSet
from ..core.utils import clone_model, is_root, last_day_of_month, namify, build_form_fake_data, get_system_cache_version
from .forms import CloneForm
from .models import Record, Registration
from ..publish.mixin import PublishMixin
from ..publish.utils import get_registration_data

logger = logging.getLogger(__name__)

DATA = {
    "registration.Registration": [],
    "core.FlexForm": [],
    "core.FormSet": [],
    "core.Validator": [],
    "core.OptionSet": [],
    "core.FlexFormField": [],
    "i18n.Message": [],
}


class JamesForm(forms.ModelForm):
    # unique_field = forms.CharField(widget=forms.HiddenInput)
    unique_field_path = forms.CharField(
        label="JMESPath expression", widget=forms.TextInput(attrs={"style": "width:90%"})
    )
    data = forms.CharField(widget=forms.Textarea, required=False)

    class Meta:
        model = Registration
        fields = ("unique_field_path", "data")

    class Media:
        js = [
            "https://cdnjs.cloudflare.com/ajax/libs/jmespath/0.16.0/jmespath.min.js",
        ]


@register(Registration)
class RegistrationAdmin(ConcurrencyVersionAdmin, PublishMixin, SmartModelAdmin):
    search_fields = ("name", "title", "slug")
    date_hierarchy = "start"
    list_filter = ("active", "archived")
    list_display = ("name", "title", "slug", "locale", "secure", "active", "validator", "archived")
    exclude = ("public_key",)
    autocomplete_fields = ("flex_form",)
    save_as = True
    readonly_fields = ("version", "last_update_date")
    formfield_overrides = {
        JSONField: {"widget": JSONEditor},
    }
    change_form_template = None
    change_list_template = None
    filter_horizontal = ("scripts",)
    fieldsets = [
        (None, {"fields": (("version", "last_update_date", "active"),)}),
        (None, {"fields": ("name", "title", "slug")}),
        (
            "Unique",
            {
                "fields": (
                    "unique_field_path",
                    "unique_field_error",
                )
            },
        ),
        ("Config", {"fields": ("flex_form", "validator", "scripts", "encrypt_data")}),
        ("Validity", {"classes": ("collapse",), "fields": (("start", "end"), ("archived", "active"))}),
        ("Languages", {"classes": ("collapse",), "fields": ("locale", "locales")}),
        ("Text", {"classes": ("collapse",), "fields": ("intro", "footer")}),
        ("Advanced", {"fields": ("advanced",)}),
        ("Others", {"fields": ("__others__",)}),
    ]

    def reversion_register(self, model, **options):
        options["exclude"] = ("version",)
        super().reversion_register(model, **options)

    def secure(self, obj):
        return bool(obj.public_key)

    secure.boolean = True

    @property
    def media(self):
        extra = "" if settings.DEBUG else ".min"
        base = super().media
        return base + forms.Media(
            js=[
                "/static/clipboard%s.js" % extra,
            ]
        )

    @view(label="invalidate cache", html_attrs={"class": "aeb-warn"})
    def invalidate_cache(self, request, pk):
        obj = self.get_object(request, pk)
        obj.save()

    @view()
    def data(self, request, registration):
        from aurora.counters.models import Counter

        qs = Counter.objects.filter(registration_id=registration).order_by("day")
        param_day = request.GET.get("d", None)
        param_tz = request.GET.get("tz", None)
        total = 0
        if param_day or param_tz:
            tz = pytz.timezone(param_tz or "utc")
            if not param_day:
                day = datetime.today().replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=tz)
            else:
                day = datetime.strptime(param_day, "%Y-%m-%d").replace(tzinfo=tz)
            start = day.astimezone(pytz.UTC)
            end = start + timedelta(days=1)
            record = qs.filter(day__gte=start, day__lt=end).first()
            data = []
            if record:
                data = record.hourly
            hours = [f"{x:02d}:00" for x in list(range(0, 24))]
            data = {
                "tz": str(tz),
                "label": day.strftime("%A, %d %B %Y"),
                "total": total,
                "date": str(day),
                "start": str(start),
                "end": str(end),
                "day": day.strftime("%Y-%m-%d"),
                "labels": hours,
                "data": data,
            }
        elif param_month := request.GET.get("m", None):
            if param_month:
                day = datetime.strptime(param_month, "%Y-%m-%d")
            else:
                day = timezone.now().today()
            qs = qs.filter(day__month=day.month)
            # qs = qs.annotate(day=TruncDay("timestamp")).values("day").annotate(c=Count("id"))
            data = defaultdict(lambda: 0)
            for record in qs.all():
                data[record.day.day] = record.records
                total += record.records

            last_day = last_day_of_month(day)
            days = list(range(1, 1 + last_day.day))
            labels = [last_day.replace(day=d).strftime("%-d, %a") for d in days]
            data = {
                "label": day.strftime("%B %Y"),
                "total": total,
                "day": day.strftime("%Y-%m-%d"),
                "labels": labels,
                "data": [data[x] for x in days],
            }
        else:
            qs = qs.all()
            data = defaultdict(lambda: 0)
            for record in qs.all():
                data[record.day] = record.records
                total += record.records
            data = {
                "label": "",
                "day": timezone.now().today().strftime("%Y-%m-%d"),
                "total": total,
                "labels": [d.strftime("%-d, %a") for d in data.keys()],
                "data": list(data.values()),
            }

        response = JsonResponse(data)
        response["Cache-Control"] = "max-age=5"
        return response

    @button()
    def inspect(self, request, pk):
        ctx = self.get_common_context(
            request,
            pk,
            media=self.media,
            title="Inspect Registration",
        )
        return render(request, "admin/registration/registration/inspect.html", ctx)

    @button()
    def clone(self, request, pk):
        ctx = self.get_common_context(
            request,
            pk,
            media=self.media,
            title="Clone Registration",
        )
        reg: Registration = ctx["original"]
        if request.method == "POST":
            form = CloneForm(request.POST)
            if form.is_valid():
                try:
                    for dip in [
                        "form_dip",
                        "field_dip",
                        "formset_dip",
                        "form_del_dip",
                        "field_del_dip",
                        "formset_del_dip",
                    ]:
                        post_save.disconnect(dispatch_uid=dip)
                        post_delete.disconnect(dispatch_uid=dip)

                    with atomic():
                        source = Registration.objects.get(id=reg.pk)
                        title = form.cleaned_data["title"]
                        reg, __ = clone_model(source, name=namify(title), title=title, version=1, slug=slugify(title))
                        if form.cleaned_data["deep"]:
                            main_form, __ = clone_model(
                                source.flex_form, name=f"{source.flex_form.name}-(clone: {reg.name})"
                            )
                            reg.flex_form = main_form
                            reg.save()
                            for fld in source.flex_form.fields.all():
                                clone_model(fld, flex_form=main_form)

                            formsets = FormSet.objects.filter(parent=source.flex_form)
                            forms = {}
                            for fs in formsets:
                                forms[fs.flex_form.pk] = fs.flex_form
                                forms[fs.parent.pk] = fs.parent

                            for frm in forms.values():
                                frm2, created = clone_model(frm, name=f"{frm.name}-(clone: {reg.name})")
                                forms[frm.pk] = frm2
                                for field in frm.fields.all():
                                    clone_model(field, name=field.name, flex_form=frm2)

                            for fs in formsets:
                                clone_model(fs, parent=forms[fs.parent.pk], flex_form=forms[fs.flex_form.pk])
                        return HttpResponseRedirect(reverse("admin:registration_registration_inspect", args=[reg.pk]))
                except Exception as e:
                    logger.exception(e)
                    self.message_error_to_user(request, e)

            else:
                ctx["form"] = form
        else:
            form = CloneForm()
            ctx["form"] = form
        return render(request, "admin/registration/registration/clone.html", ctx)

    @button()
    def create_translation(self, request, pk):
        from aurora.i18n.forms import TranslationForm
        from aurora.i18n.models import Message

        ctx = self.get_common_context(
            request,
            pk,
            media=self.media,
            title="Generate Translation",
        )
        instance: Registration = ctx["original"]
        if request.method == "POST":
            form = TranslationForm(request.POST)
            if form.is_valid():
                locale = form.cleaned_data["locale"]
                existing = Message.objects.filter(locale=locale).count()
                uri = reverse("register", args=[instance.slug, instance.version])
                uri = translate_url(uri, locale)
                from django.test import Client

                settings.ALLOWED_HOSTS.append("testserver")
                headers = {"HTTP_ACCEPT_LANGUAGE": "locale", "HTTP_I18N": "true"}
                try:
                    client = Client(**headers)
                    r1 = client.get(uri)
                    # uri = request.build_absolute_uri(reverse("register", args=[instance.slug]))
                    # uri = translate_url(uri, locale)
                    # r1 = requests.get(uri, headers={"Accept-Language": locale, "I18N": "true"})
                    if r1.status_code == 302:
                        # return HttpResponse(r1.content, status=r1.status_code)
                        raise Exception(f"GET: {uri} - {r1.status_code}: {r1.headers['location']}")
                    if r1.status_code != 200:
                        # return HttpResponse(r1.content, status=r1.status_code)
                        raise Exception(f"GET: {uri} - {r1.status_code}")
                    # r2 = requests.post(uri, {}, headers={"Accept-Language": locale, "I18N": "true"})
                    r2 = client.post(uri, {}, **headers)
                    if r2.status_code != 200:
                        # return HttpResponse(r2.content, status=r2.status_code)
                        raise Exception(f"POST: {uri} - {r2.status_code}")
                except Exception as e:
                    logger.exception(e)
                    self.message_error_to_user(request, e)

                updated = Message.objects.filter(locale=locale).count()
                added = Message.objects.filter(locale=locale, draft=True, timestamp__date=today())
                self.message_user(request, f"{updated - existing} messages created. {updated} available")
                ctx["uri"] = uri
                ctx["locale"] = locale
                ctx["added"] = added
            else:
                ctx["form"] = form
        else:
            form = TranslationForm()
            ctx["form"] = form
        return render(request, "admin/registration/registration/translation.html", ctx)

    @view()
    def removekey(self, request, pk):
        ctx = self.get_common_context(request, pk, title="Remove Encryption Key")
        if request.method == "POST":
            self.object = self.get_object(request, pk)
            self.object.public_key = ""
            self.object.save()
            self.message_user(request, "Encryption key removed", messages.WARNING)
            self.log_change(request, self.object, "Encryption Key has been removed")
            return HttpResponseRedirect("..")
        else:
            return render(request, "admin/registration/registration/keys_remove.html", ctx)

    @view()
    def generate_keys(self, request, pk):
        ctx = self.get_common_context(
            request, pk, media=self.media, title="Generate Private/Public Key pair to encrypt this Registration data"
        )

        if request.method == "POST":
            ctx["title"] = "Key Pair Generated"
            private_pem, public_pem = self.object.setup_encryption_keys()
            ctx["private_key"] = private_pem
            ctx["public_key"] = public_pem
            self.log_change(request, self.object, "Encryption Keys have been generated")

        return render(request, "admin/registration/registration/keys.html", ctx)

    @link(permission=is_root, html_attrs={"class": "aeb-warn "})
    def view_collected_data(self, button):
        try:
            if button.original:
                base = reverse("admin:registration_record_changelist")
                button.href = f"{base}?registration__exact={button.original.pk}"
                button.html_attrs["target"] = f"_{button.original.pk}"
        except Exception as e:
            logger.exception(e)

    @view()
    def james_fake_data(self, request, pk):
        reg = self.get_object(request, pk)
        data = cache.get(f"james_{pk}", version=get_system_cache_version())
        if not data:
            form_class = reg.flex_form.get_form_class()
            data = json.dumps(build_form_fake_data(form_class))
            cache.set(f"james_{pk}", data, version=get_system_cache_version())

        return JsonResponse(json.loads(data), safe=False)

    @button()
    def james_editor(self, request, pk):
        ctx = self.get_common_context(request, pk, title="JAMESPath Editor")
        if request.method == "POST":
            form = JamesForm(request.POST, instance=ctx["original"])
            if form.is_valid():

                form.save()
                cache.set(f"james_{pk}", form.cleaned_data["data"], version=get_system_cache_version())
                return HttpResponseRedirect(".")
        else:
            data = cache.get(f"james_{pk}", version=get_system_cache_version())
            form = JamesForm(instance=ctx["original"], initial={"data": data})
        ctx["form"] = form
        return render(request, "admin/registration/registration/james_editor.html", ctx)

    @button()
    def test(self, request, pk):
        ctx = self.get_common_context(request, pk, title="Test")
        form = self.object.flex_form.get_form_class()
        ctx["registration"] = self.object
        ctx["form"] = form
        return render(request, "admin/registration/registration/test.html", ctx)

    def get_changeform_buttons(self, context):
        return sorted(
            [h for h in self.extra_button_handlers.values() if h.change_form in [True, None]],
            key=lambda item: item.config.get("order", 1),
        )

    def get_changelist_buttons(self, context):
        return sorted(
            [h for h in self.extra_button_handlers.values() if h.change_list in [True, None]],
            key=lambda item: item.config.get("order", 1),
        )

    def _get_data(self, record):
        return get_registration_data(record)


class DecryptForm(forms.Form):
    key = forms.CharField(widget=forms.Textarea)


class HourFilter(SimpleListFilter):
    parameter_name = "hours"
    title = "Latest [n] hours"
    slots = (
        (30, _("30 min")),
        (60, _("1 hour")),
        (60 * 4, _("4 hour")),
        (60 * 6, _("6 hour")),
        (60 * 8, _("8 hour")),
        (60 * 12, _("12 hour")),
        (60 * 24, _("24 hour")),
    )

    def lookups(self, request, model_admin):
        return self.slots

    def queryset(self, request, queryset):
        if self.value():
            offset = datetime.now() - timedelta(minutes=int(self.value()))
            queryset = queryset.filter(timestamp__gte=offset)

        return queryset


@register(Record)
class RecordAdmin(SmartModelAdmin):
    date_hierarchy = "timestamp"
    search_fields = ("registration__name",)
    list_display = ("timestamp", "remote_ip", "id", "registration", "ignored", "unique_field")
    readonly_fields = ("registration", "timestamp", "remote_ip", "id", "fields", "counters")
    autocomplete_fields = ("registration",)
    list_filter = (("registration", AutoCompleteFilter), HourFilter, ("unique_field", ValueFilter), "ignored")
    change_form_template = None
    change_list_template = None
    actions = ["fix_tax_id"]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related("registration")
        return qs

    def get_common_context(self, request, pk=None, **kwargs):
        return super().get_common_context(request, pk, is_root=is_root(request), **kwargs)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = {"is_root": is_root(request)}
        return super().changeform_view(request, object_id, form_url, extra_context)

    def fix_tax_id(self, request, queryset):
        results = {"updated": [], "processed": []}
        for record in queryset:
            try:
                for individual in record.fields["individuals"]:
                    if individual["role_i_c"] == "y":
                        record.unique_field = individual["tax_id_no_i_c"]
                        record.save()
                        results["updated"].append(record.pk)
                        break
                results["processed"].append(record.pk)

            except Exception as e:
                results[record.pk] = f"{e.__class__.__name__}: {str(e)}"
        return JsonResponse(results)

    @button(label="Fix TaxID")
    def _fix_tax_id(self, request):
        queryset = Record.objects.filter(unique_field__isnull=True, timestamp__gt="2022-06-15")
        return self.fix_tax_id(request, queryset)

    @link(html_attrs={"class": "aeb-warn "}, change_form=True)
    def receipt(self, button):
        try:
            if button.original:
                base = reverse("register-done", args=[button.original.registration.pk, button.original.pk])
                button.href = base
                button.html_attrs["target"] = f"_{button.original.pk}"
        except Exception as e:
            logger.exception(e)

    @button(label="Preview", permission=is_root)
    def preview(self, request, pk):
        ctx = self.get_common_context(request, pk, title="Preview")

        return render(request, "admin/registration/record/preview.html", ctx)

    @button(label="inspect", permission=is_root)
    def inspect(self, request, pk):
        ctx = self.get_common_context(request, pk, title="Inspect")
        ctx["files_as_dict"] = json.loads(self.object.files.tobytes().decode())
        return render(request, "admin/registration/record/inspect.html", ctx)

    @button(permission=is_root)
    def decrypt(self, request, pk):
        ctx = self.get_common_context(request, pk, title="To decrypt you need to provide Registration Private Key")
        if request.method == "POST":
            form = DecryptForm(request.POST)
            ctx["title"] = "Data have been decrypted only to be showed on this page. Still encrypted on the DB"
            if form.is_valid():
                key = form.cleaned_data["key"]
                try:
                    ctx["decrypted"] = self.object.decrypt(key)
                except Exception as e:
                    ctx["title"] = "Error decrypting data"
                    self.message_error_to_user(request, e)
        else:
            form = DecryptForm()

        ctx["form"] = form
        return render(request, "admin/registration/record/decrypt.html", ctx)

    def get_readonly_fields(self, request, obj=None):
        if is_root(request) or settings.DEBUG:
            return []
        return self.readonly_fields

    def has_view_permission(self, request, obj=None):
        return is_root(request) or settings.DEBUG

    def has_add_permission(self, request):
        return is_root(request) or settings.DEBUG

    def has_delete_permission(self, request, obj=None):
        return settings.DEBUG

    def has_change_permission(self, request, obj=None):
        return is_root(request) or settings.DEBUG
