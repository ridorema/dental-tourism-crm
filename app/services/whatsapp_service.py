STATUS_TEMPLATES_IT = {
    "new": "Ciao {first_name}, grazie per aver contattato {clinic_name}. Ti va bene una chiamata veloce oggi?",
    "contacted": "Ciao {first_name}, ti scrivo per un follow-up. Hai domande sul trattamento o sui tempi del viaggio?",
    "quoted": "Ciao {first_name}, ti abbiamo inviato il preventivo di {quote_total} {currency}. Posso aiutarti a confermare la data?",
    "appointment_reminder": "Promemoria appuntamento: {appointment_date} alle {appointment_time}. Ti aspettiamo alla {clinic_name}.",
}


def render_whatsapp_template(status, context):
    template = STATUS_TEMPLATES_IT.get(status)
    if not template:
        return ""
    return template.format(**context)
