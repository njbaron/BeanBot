import hikari
import miru


class YesNoView(miru.View):
    def __init__(self, default_result: bool = False, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.result = default_result

    @miru.button(label="Yes", style=hikari.ButtonStyle.SUCCESS)
    async def yes_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.result = True
        self.stop()

    @miru.button(label="No", style=hikari.ButtonStyle.DANGER)
    async def no_button(self, button: miru.Button, ctx: miru.Context) -> None:
        self.result = False
        self.stop()
