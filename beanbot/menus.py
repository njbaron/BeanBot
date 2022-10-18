import hikari
import lightbulb
import miru
import lavalink

from typing import Any, List, Optional

import logging

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

    async def send(self, ctx: lightbulb.Context, message: str) -> bool:
        resp = await ctx.respond(message, components=self.build())
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


class _TrackSelect(miru.Select):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    async def callback(self, ctx: miru.Context) -> None:
        self.view.result = self.view.find_track_from_id(ctx.interaction.values[0])
        self.view.stop()


class TrackSelectView(ResultView):
    def __init__(
        self,
        possable_results: List[lavalink.AudioTrack],
        placeholder: str,
        default_result: Any = None,
        delete_on_answer: bool = True,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(default_result, delete_on_answer, *args, **kwargs)

        self.track_results = possable_results
        select_options = [
            miru.SelectOption(
                track.title,
                track.identifier,
                description=track.uri,
                is_default=(index == 0),
            )
            for index, track in enumerate(possable_results)
        ]
        select_component = _TrackSelect(options=select_options, placeholder=placeholder)
        self.add_item(select_component)

    def find_track_from_id(self, track_id: str) -> lavalink.AudioTrack:
        for track in self.track_results:
            if track.identifier == track_id:
                return track
        return None

    @miru.button(label="Cancel", style=hikari.ButtonStyle.DANGER)
    async def cancel_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.stop()
