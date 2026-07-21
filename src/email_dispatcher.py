import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


class EmailDispatcher:
    def __init__(self, smtp_address: str, smtp_app_password: str, company_name: str):
        self.smtp_address = smtp_address
        self.smtp_app_password = smtp_app_password
        self.company_name = company_name
        self._env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))

    def render(self, fields: dict) -> str:
        template = self._env.get_template("alert_email.html")
        return template.render(company_name=self.company_name, **fields)

    def send(self, to_addresses: list[str], subject: str, fields: dict) -> None:
        if not to_addresses:
            return

        html_body = self.render(fields)

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.company_name} Alerts <{self.smtp_address}>"
        msg["To"] = ", ".join(to_addresses)
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(self.smtp_address, self.smtp_app_password)
            server.sendmail(self.smtp_address, to_addresses, msg.as_string())
