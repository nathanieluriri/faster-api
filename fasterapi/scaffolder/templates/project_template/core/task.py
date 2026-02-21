from core.queue.tasks import task
from repositories.tokens_repo import delete_access_and_refresh_token_with_user_id


@task("delete_tokens")
async def delete_tokens_task(userId: str) -> bool:
    return await delete_access_and_refresh_token_with_user_id(userId=userId)
