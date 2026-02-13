def send_quote_email_stub(quote, recipient_email):
    # Stub for future integration with SMTP/SendGrid/Postmark.
    return {
        "sent": True,
        "recipient": recipient_email,
        "subject": f"Your Quote #{quote.id}",
    }
