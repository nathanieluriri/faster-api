from core.email.manager import EmailManager
from core.email.types import EmailDispatchRequest
from core.queue.tasks import task
from repositories.tokens_repo import delete_access_and_refresh_token_with_user_id


@task("delete_tokens")
async def delete_tokens_task(userId: str) -> bool:
    return await delete_access_and_refresh_token_with_user_id(userId=userId)


@task("send_email")
async def send_email_task(to_email: str, template_key: str, context: dict | None = None) -> bool:
    manager = EmailManager.get_instance()
    await manager.send_template(
        EmailDispatchRequest(
            to_email=to_email,
            template_key=template_key,
            context=context or {},
            dispatch="sync",
        )
    )
    return True
