import logging
from typing import Any

import hikari
import lightbulb
import miru


logger = logging.getLogger(__name__)


class ResultView(miru.View):
    def __init__(
        self,
        default_result: Any = None,
        delete_on_answer: bool = True,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.result = default_result
        self.delete_on_answer = delete_on_answer

        self.requester_id = None

    async def view_check(self, ctx: miru.Context) -> bool:
        return ctx.user.id == self.requester_id

    async def send(self, ctx: lightbulb.Context, message: str = "", embed: hikari.Embed = None) -> bool:
        self.requester_id = ctx.user.id
        resp = await ctx.respond(message, embed=embed, components=self.build())
        msg = await resp.message()
        await self.start(msg)
        await self.wait()
        if self.delete_on_answer:
            await msg.delete()
        else:
            await msg.edit(components=None)
        return self.result


class YesNoView(ResultView):
    def __init__(
        self,
        default_result: bool = False,
        delete_on_answer: bool = True,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)

        self.result = default_result
        self.delete_on_answer = delete_on_answer

    @miru.button(label="Yes", style=hikari.ButtonStyle.SUCCESS)
    async def yes_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.result = True
        self.stop()

    @miru.button(label="No", style=hikari.ButtonStyle.DANGER)
    async def no_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.result = False
        self.stop()
