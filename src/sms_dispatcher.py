import boto3


class SmsDispatcher:
    """Sends SMS via AWS SNS (swapped in for Twilio per project decision).

    Requires an AWS account with SNS access and, in most regions/accounts,
    an origination identity (or the account moved out of SNS sandbox mode)
    for one-way transactional SMS.
    """

    def __init__(self, region: str, company_name: str):
        self._client = boto3.client("sns", region_name=region)
        self.company_name = company_name

    def send(self, phone_numbers: list[str], message: str) -> None:
        for phone_number in phone_numbers:
            self._client.publish(
                PhoneNumber=phone_number,
                Message=message,
                MessageAttributes={
                    "AWS.SNS.SMS.SMSType": {
                        "DataType": "String",
                        "StringValue": "Transactional",
                    }
                },
            )
