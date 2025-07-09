import os

# Create global instance
if os.getenv("GIGACHAT_DRYRUN", "false").lower() == "true":
    from gigachat_dryrun import DryRunGigaChatService
    gigachat_service = DryRunGigaChatService()
else:
    from gigachat_service import GigaChatService
    gigachat_service = GigaChatService()
