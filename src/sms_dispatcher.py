import boto3


class SmsDispatcher:
    """Sends SMS via AWS SNS (swapped in for Twilio per project decision).

    Requires an AWS account with SNS access and, for most destination
    countries (UK included), an approved origination identity — a
    registered Sender ID — for that country. Without one, AWS rejects
    sends (and sandbox verification) with "No origination entities
    available to send".
    """

    def __init__(self, region: str, company_name: str, sender_id: str | None = None):
        self._client = boto3.client("sns", region_name=region)
        self.company_name = company_name
        self.sender_id = sender_id

    def send(self, phone_numbers: list[str], message: str) -> None:
        message_attributes = {
            "AWS.SNS.SMS.SMSType": {
                "DataType": "String",
                "StringValue": "Transactional",
            }
        }
        if self.sender_id:
            message_attributes["AWS.SNS.SMS.SenderID"] = {
                "DataType": "String",
                "StringValue": self.sender_id,
            }

        for phone_number in phone_numbers:
            self._client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes=message_attributes,
            )
