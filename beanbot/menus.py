import logging
from typing import Any, List, Optional

import hikari
import lavalink
import lightbulb
import miru

from beanbot import constants

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

    async def send(
        self, ctx: lightbulb.Context, message: str = "", embed: hikari.Embed = None
    ) -> bool:
        self.requester_id = ctx.user.id
        resp = await ctx.respond(message, embed=embed, components=self.build())
        msg = await resp.message()
        self.start(msg)
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


class QuestionSelect(miru.Select):
    def __init__(self, question: str, answers: List[str], max_values: int = 1) -> None:
        self.choices = answers
        self.question = question
        select_options = [
            miru.SelectOption(
                option_str,
                option_str,
            )
            for index, option_str in enumerate(
                answers[: constants.MenuConstants.MAX_SELECT_OPTIONS]
            )
        ]
        super().__init__(
            options=select_options, placeholder=question, max_values=max_values
        )

    async def callback(self, ctx: miru.Context) -> None:
        logger.info(f"Selected {ctx.interaction.values}")
        self.view.answers[self.question] = " ".join(ctx.interaction.values)
        # self.placeholder = ctx.interaction.values[0]


class QuestionView(ResultView):
    def __init__(self, select_questions: List[QuestionSelect], *args, **kwargs) -> None:
        super().__init__(False, True, *args, **kwargs)
        self.answers = {}
        self.number_of_questions = len(select_questions)

        for select in select_questions:
            self.add_item(select)

    @miru.button(label="Done", style=hikari.ButtonStyle.SUCCESS)
    async def done_button(self, button: miru.Button, ctx: miru.Context) -> None:
        if len(self.answers.keys()) >= self.number_of_questions:
            self.result = True
            self.stop()
        else:
            await ctx.respond("Please finish answering the questions.")

    @miru.button(label="Cancel", style=hikari.ButtonStyle.DANGER)
    async def cancel_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.result = False
        self.stop()
