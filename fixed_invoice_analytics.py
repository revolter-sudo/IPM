# Invoice Analytics API
@admin_app.get(
    "/projects/{project_id}/invoice-analytics",
    tags=["Invoice Analytics"],
    description="""
    Get invoice analytics for a project with is_late flag based on payment dates vs project end date.

    The is_late flag logic:
    - True: Invoice payment is paid after project end date OR not yet paid and project end date has passed
    - False: Invoice payment is paid before project end date
    - None: Not yet paid and project end date has not passed
    """
)
def get_project_invoice_analytics(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get invoice analytics for a project with is_late flag.
    """
    try:
        # Verify user has permission
        if current_user.role not in [
            UserRole.SUPER_ADMIN.value,
            UserRole.ADMIN.value,
            UserRole.ACCOUNTANT.value,
            UserRole.PROJECT_MANAGER.value,
        ]:
            return ProjectServiceResponse(
                data=None,
                status_code=403,
                message="Not authorized to view invoice analytics"
            ).model_dump()

        # Find the project
        project = db.query(Project).filter(
            Project.uuid == project_id,
            Project.is_deleted.is_(False)
        ).first()

        if not project:
            return ProjectServiceResponse(
                data=None,
                status_code=404,
                message="Project not found"
            ).model_dump()

        # Get all invoices for this project
        invoices = db.query(Invoice).filter(
            Invoice.project_id == project_id,
            Invoice.is_deleted.is_(False)
        ).all()

        # Get all POs for this project
        project_pos = db.query(ProjectPO).filter(
            ProjectPO.project_id == project_id,
            ProjectPO.is_deleted.is_(False)
        ).all()

        # Create PO lookup
        po_lookup = {po.uuid: po for po in project_pos}

        # Process each invoice
        invoice_analytics = []
        from datetime import date
        today = date.today()

        for invoice in invoices:
            # Get PO details
            po_number = None
            po_amount = 0.0
            if invoice.project_po_id and invoice.project_po_id in po_lookup:
                po = po_lookup[invoice.project_po_id]
                po_number = po.po_number
                po_amount = po.amount

            # Get all payments for this invoice to determine latest payment date
            payments = db.query(InvoicePayment).filter(
                InvoicePayment.invoice_id == invoice.uuid,
                InvoicePayment.is_deleted.is_(False)
            ).order_by(InvoicePayment.payment_date.desc()).all()

            # Determine is_late flag
            is_late = None
            if project.end_date:
                if invoice.payment_status == "fully_paid" and payments:
                    # Check if any payment was made after project end date
                    latest_payment_date = max(payment.payment_date for payment in payments)
                    is_late = latest_payment_date > project.end_date
                elif invoice.payment_status == "partially_paid" and payments:
                    # For partially paid, check if the latest payment was after end date
                    latest_payment_date = max(payment.payment_date for payment in payments)
                    is_late = latest_payment_date > project.end_date
                elif invoice.payment_status == "not_paid":
                    # Not paid and project end date has passed
                    is_late = today > project.end_date
                else:
                    is_late = None

            invoice_analytics.append(InvoiceAnalyticsItem(
                invoice_uuid=invoice.uuid,
                project_name=project.name,
                po_number=po_number,
                po_amount=po_amount,
                invoice_amount=invoice.amount,
                invoice_due_date=invoice.due_date.strftime("%Y-%m-%d"),
                payment_status=invoice.payment_status,
                total_paid_amount=invoice.total_paid_amount,
                is_late=is_late
            ))

        # Create response
        analytics_response = InvoiceAnalyticsResponse(
            project_id=project_id,
            project_name=project.name,
            project_end_date=project.end_date.strftime("%Y-%m-%d") if project.end_date else None,
            invoices=invoice_analytics
        )

        return ProjectServiceResponse(
            data=analytics_response.model_dump(),
            message="Invoice analytics fetched successfully",
            status_code=200
        ).model_dump()

    except Exception as e:
        logging.error(f"Error in get_project_invoice_analytics API: {str(e)}")
        return ProjectServiceResponse(
            data=None,
            status_code=500,
            message=f"An error occurred while fetching invoice analytics: {str(e)}"
        ).model_dump()