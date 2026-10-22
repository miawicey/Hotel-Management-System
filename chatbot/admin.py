from django.contrib import admin, messages
from django.utils.html import format_html

from .models import (
    RoomServiceMenuItem,
    ServiceOrder,
    ServiceOrderItem,
    ServiceOrderStatusLog,
)


@admin.register(RoomServiceMenuItem)
class RoomServiceMenuItemAdmin(admin.ModelAdmin):
    list_display = (
        'name', 'category', 'subcategory', 'price', 'is_recommended',
        'prep_minutes', 'is_available', 'sort_order',
    )
    list_filter = (
        'category', 'subcategory', 'is_recommended', 'is_available',
        'is_spicy', 'is_vegetarian',
    )
    list_editable = ('price', 'is_recommended', 'is_available', 'sort_order')
    search_fields = ('name', 'description')
    ordering = ('category', 'subcategory', 'sort_order', 'name')
    readonly_fields = ('image_preview',)
    fieldsets = (
        ('Identitas menu', {
            'fields': ('name', 'description', 'category', 'subcategory'),
        }),
        ('Harga & penyajian', {
            'fields': ('price', 'prep_minutes', 'is_spicy', 'is_vegetarian'),
        }),
        ('Tampilan portal', {
            'fields': ('image_url', 'image_preview', 'is_recommended', 'is_available', 'sort_order'),
        }),
    )

    @admin.display(description='Pratinjau')
    def image_preview(self, obj):
        if not obj.image_url:
            return '—'
        return format_html(
            '<img src="{}" alt="" style="max-width:260px;max-height:150px;'
            'border-radius:10px;object-fit:cover;">',
            obj.image_url,
        )


class ServiceOrderItemInline(admin.TabularInline):
    model = ServiceOrderItem
    extra = 0
    readonly_fields = ('name', 'unit_price', 'quantity')
    can_delete = False


class ServiceOrderStatusLogInline(admin.TabularInline):
    model = ServiceOrderStatusLog
    extra = 0
    readonly_fields = ('status', 'note', 'changed_by', 'created_at')
    can_delete = False


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = (
        'order_code_display', 'user', 'fulfillment', 'status', 'booking',
        'item_count', 'total', 'created_at',
    )
    list_filter = ('fulfillment', 'service_type', 'status', 'created_at')
    search_fields = (
        'user__username', 'user__email', 'detail', 'special_instructions',
    )
    list_select_related = ('user', 'booking', 'booking__room')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ServiceOrderItemInline, ServiceOrderStatusLogInline]
    date_hierarchy = 'created_at'
    actions = (
        'tandai_diproses', 'tandai_siap_restoran', 'tandai_diantar',
        'tandai_dibatalkan',
    )

    @admin.display(description='Pesanan', ordering='pk')
    def order_code_display(self, obj):
        return obj.order_code

    @admin.display(description='Item')
    def item_count(self, obj):
        return obj.item_count or '-'

    @admin.display(description='Total')
    def total(self, obj):
        return f'Rp {obj.total:,.0f}'.replace(',', '.') if obj.items.exists() else '-'

    def _set_status(self, request, queryset, status, note):
        updated = 0
        rejected = 0
        for order in queryset:
            if order.transition_to(status, actor=request.user, note=note):
                updated += 1
            else:
                rejected += 1
        if updated:
            self.message_user(
                request,
                f'{updated} pesanan dipindahkan ke "{status}".',
            )
        if rejected:
            self.message_user(
                request,
                f'{rejected} pesanan tidak dapat dipindahkan ke "{status}" '
                'karena metode penyajian atau statusnya tidak sesuai.',
                level=messages.WARNING,
            )

    @admin.action(description='Proses di dapur (Pesanan Masuk → Diproses)')
    def tandai_diproses(self, request, queryset):
        self._set_status(
            request, queryset, ServiceOrder.STATUS_PROCESSING,
            'Pesanan mulai diproses oleh dapur.',
        )

    @admin.action(description='Siap di restoran (untuk pickup / dine-in)')
    def tandai_siap_restoran(self, request, queryset):
        self._set_status(
            request, queryset, ServiceOrder.STATUS_READY,
            'Pesanan siap disajikan di The Grand Dining & Lounge.',
        )

    @admin.action(description='Diantar ke kamar (untuk delivery)')
    def tandai_diantar(self, request, queryset):
        self._set_status(
            request, queryset, ServiceOrder.STATUS_DELIVERED,
            'Pesanan telah diantar ke kamar tamu.',
        )

    @admin.action(description='Batalkan pesanan')
    def tandai_dibatalkan(self, request, queryset):
        self._set_status(
            request, queryset, ServiceOrder.STATUS_CANCELLED,
            'Pesanan dibatalkan oleh staf.',
        )


@admin.register(ServiceOrderStatusLog)
class ServiceOrderStatusLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'status', 'changed_by', 'created_at')
    list_filter = ('status',)
    readonly_fields = ('order', 'status', 'note', 'changed_by', 'created_at')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
