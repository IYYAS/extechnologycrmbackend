from decimal import Decimal

def apply_advances_to_invoice(invoice, limit_amount=None):
    """
    Automatically applies existing manual advances to a new invoice.
    Consumes advances chronologically until the invoice is paid or advances run out.
    If limit_amount is provided, it only applies up to that specific amount.
    """
    remaining_to_apply = limit_amount if limit_amount is not None else invoice.balance_due
    
    if remaining_to_apply <= 0 or invoice.balance_due <= 0:
        return

    from .models import ClientAdvance, Payment
    from django.db.models import F
    
    # Find advances with remaining balance
    advances = ClientAdvance.objects.filter(
        client=invoice.client_company,
        remaining_amount__gt=0
    ).order_by('created_at')

    for adv in advances:
        # Amount available in this advance vs what we need for invoice vs our limit
        amount_to_apply = min(adv.remaining_amount, invoice.balance_due, remaining_to_apply)
        if amount_to_apply <= 0:
            continue

        # Create a "Shadow Payment" representing the application of the advance
        # This will trigger process_payment_accounting(pay) which updates invoice totals.
        pay = Payment.objects.create(
            invoice=invoice,
            amount=amount_to_apply,
            payment_method="Advance Applied",
            advance_applied=adv,
            notes=f"Applied from Advance {adv.id}"
        )

        # Re-fetch invoice from DB to get the updated totals from process_payment_accounting
        invoice.refresh_from_db()
        remaining_to_apply -= amount_to_apply
        
        if invoice.balance_due <= 0 or remaining_to_apply <= 0:
            break

def process_payment_accounting(payment):
    """
    Centralized ERP-grade accounting logic for a payment.
    Ensures no negative balances and correct advance splitting.
    """
    from django.db import transaction
    
    with transaction.atomic():
        invoice = payment.invoice
        if not invoice:
            return
            
        client = invoice.client_company
        if not client:
            return

        # 1. Calculate split (Invoice vs Advance)
        remaining = max(Decimal("0.00"), invoice.total_amount - invoice.total_paid)
        payment_amount = payment.amount
        
        invoice_payment = min(payment_amount, remaining)
        advance_amount = payment_amount - invoice_payment
            
        # 2. Update Invoice
        invoice.total_paid += invoice_payment
        invoice.balance_due = max(Decimal("0.00"), invoice.total_amount - invoice.total_paid)
        
        if invoice.balance_due == 0:
            invoice.status = "PAID"
        elif invoice.total_paid > 0:
            invoice.status = "PARTIAL"
        else:
            invoice.status = "UNPAID"
            
        invoice.save(update_fields=["total_paid", "balance_due", "status"])
        
        # 3. Handle Advance
        if advance_amount > 0:
            from .models import ClientAdvance
            ClientAdvance.objects.create(
                client=client,
                amount=advance_amount,
                advance_balance=advance_amount,
                remaining_amount=advance_amount,
                is_manual=False,
                note=f"Automatic advance from overpayment of {invoice.invoice_number}"
            )

def sync_client_advances(client):
    """
    NUCLEAR RECONCILIATION: Syncs advance balances by rebuilding from historical records.
    (This ensures manual adjustments and shadow payments are accurately reflected.)
    """
    from django.db import transaction
    from django.db.models import F
    from .models import Payment, ClientAdvance
    
    with transaction.atomic():
        # 1. Recalculate Advance Remaining Balances
        # First reset to amount minus initial_usage (manual adjustments)
        ClientAdvance.objects.filter(client=client).update(
            remaining_amount=F('amount') - F('initial_usage'),
            advance_balance=F('amount') - F('initial_usage')
        )
        
        # 2. Subtract all applications (Shadow Payments)
        # This scans the history of all payments that were "Advance Applied" 
        # out of specific advances for this client.
        for pay in Payment.objects.filter(invoice__client_company=client, advance_applied__isnull=False):
            adv = pay.advance_applied
            ClientAdvance.objects.filter(id=adv.id).update(
                remaining_amount=F('remaining_amount') - pay.amount
            )
