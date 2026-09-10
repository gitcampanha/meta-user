import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage

import requests

ARQUIVO = "relatorio.pdf"
HOJE = datetime.now().strftime("%d/%m/%Y")


def enviar_email():
    remetente = os.environ["EMAIL_REMETENTE"]
    senha = os.environ["EMAIL_SENHA_APP"]
    destinos = [d.strip() for d in os.environ["EMAIL_DESTINO"].split(",")]

    msg = EmailMessage()
    msg["Subject"] = f"Relatório de tráfego — {HOJE}"
    msg["From"] = remetente
    msg["To"] = ", ".join(destinos)
    msg.set_content(
        f"Segue em anexo o relatório diário de tráfego pago da campanha ({HOJE}).\n\n"
        "Enviado automaticamente pelo monitoramento."
    )
    with open(ARQUIVO, "rb") as f:
        msg.add_attachment(f.read(), maintype="application",
                           subtype="pdf", filename=f"relatorio_{HOJE.replace('/', '-')}.pdf")

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(remetente, senha)
        s.send_message(msg)
    print("E-mail enviado para:", destinos)


def enviar_telegram():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    url = f"https://api.telegram.org/bot{token}/sendDocument"
    with open(ARQUIVO, "rb") as f:
        r = requests.post(
            url,
            data={"chat_id": chat_id,
                  "caption": f"📊 Relatório de tráfego — {HOJE}"},
            files={"document": (f"relatorio_{HOJE.replace('/', '-')}.pdf", f,
                                "application/pdf")},
            timeout=60,
        )
    r.raise_for_status()
    print("Telegram enviado, message_id:",
          r.json().get("result", {}).get("message_id"))


if __name__ == "__main__":
    erros = []
    for nome, fn in [("e-mail", enviar_email), ("Telegram", enviar_telegram)]:
        try:
            fn()
        except Exception as e:
            erros.append(f"{nome}: {e}")
    if erros:
        raise SystemExit("Falhas no envio -> " + " | ".join(erros))
