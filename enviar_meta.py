"""Entrega nos canais existentes; nao exibe credenciais nem destinatarios em logs."""
import os
import smtplib
from pathlib import Path
from email.message import EmailMessage
import requests

def main():
    path = Path(Path('relatorio_path.txt').read_text().strip())
    failures = []
    token, chat = os.getenv('TG_TOKEN','').strip(), os.getenv('TG_CHAT','').strip()
    if token and chat:
        try:
            with path.open('rb') as source:
                response = requests.post(f'https://api.telegram.org/bot{token}/sendDocument', data={'chat_id':chat,'caption':'Relatorio de dados Meta'},files={'document':source},timeout=60)
            if response.status_code != 200 or not response.json().get('ok'):
                raise RuntimeError('Falha no Telegram')
            print('Telegram: entrega confirmada')
        except Exception:
            failures.append('Telegram: entrega nao confirmada')
    else:
        print('Telegram: canal nao configurado')
    user, password = os.getenv('GMAIL_USER','').strip(), os.getenv('GMAIL_PASS','').strip()
    recipients = [x.strip() for x in (os.getenv('EMAIL_TO','').strip() or user).split(',') if x.strip()]
    if user and password and recipients:
        try:
            message = EmailMessage()
            message['Subject'] = 'Relatorio de dados Meta'
            message['From'] = user
            message['To'] = ', '.join(recipients)
            message.set_content('Relatorio descritivo em anexo. Dados indisponiveis e limites de mensuracao estao identificados no PDF.')
            message.add_attachment(path.read_bytes(),maintype='application',subtype='pdf',filename=path.name)
            with smtplib.SMTP_SSL('smtp.gmail.com',465,timeout=60) as smtp:
                smtp.login(user,password)
                if smtp.send_message(message):
                    raise RuntimeError('Destinatarios recusados')
            print('Email: entrega aceita pelo servidor')
        except Exception:
            failures.append('Email: entrega nao confirmada')
    else:
        print('Email: canal nao configurado')
    if failures:
        raise SystemExit('; '.join(failures))

if __name__ == '__main__':
    main()
