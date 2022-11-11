import asyncio
import json
import logging
import copy
import time
from datetime import timedelta
from typing import List

import aiohttp
import lightbulb
import hikari

import io
import base64
from PIL import Image, PngImagePlugin

from beanbot import config

logger = logging.getLogger(__name__)

ai_plugin = lightbulb.Plugin(name="AI", description="Using ai to do things.")

REQUEST_TEMPLATE = {
    "prompt": "",
    "negative_prompt": "",
    "steps": 50,
    "width": 512,
    "height": 512,
    "sampler_index": "Euler",
    "seed": -1,
    "subseed": -1,
    "subseed_strength": 0,
    "enable_hr": False,
    "restore_faces": False,
    "tiling": False,
    "denoising_strength": 0,
    "firstphase_width": 0,
    "firstphase_height": 0,
    "styles": ["string"],
    "cfg_scale": 7,
    "seed_resize_from_h": -1,
    "seed_resize_from_w": -1,
    "batch_size": 1,
    "n_iter": 1,
    "eta": 0,
    "s_churn": 0,
    "s_tmax": 0,
    "s_tmin": 0,
    "s_noise": 1,
    "override_settings": {},
}


class StableDiffustionEndpoints:
    SAMPLERS: str = "/sdapi/v1/samplers"
    MODELS: str = "/sdapi/v1/sd-models"
    PROGRESS: str = "/sdapi/v1/progress"
    TEXT2IMG: str = "/sdapi/v1/txt2img"
    IMG2IMG: str = "/sdapi/v1/img2img"


def get_aiohttp_client(bot: lightbulb.BotApp) -> aiohttp.ClientSession:
    return bot.d.aio_session





message_tasks = {}


@ai_plugin.command
@lightbulb.option(
    "prompt", "The text to use the generate the image.", type=str, required=True
)
@lightbulb.option(
    "negative_prompt",
    "Text used that is excluded from the images.",
    type=str,
    default="",
    required=False,
)
@lightbulb.option(
    "steps",
    "The number of steps to use to develop the image.",
    type=int,
    min_value=1,
    max_value=150,
    default=50,
    required=False,
)
@lightbulb.option(
    "model",
    "The sd weights to use to make the image.",
    choices=["default"],
    required=False,
)
@lightbulb.option(
    "sampler",
    "The sampler to use to make the image.",
    choices=[
        "Euler a",
        "Euler",
        "LMS",
        "Heun",
        "DPM2",
        "DPM2 a",
        "DPM fast",
        "DPM adaptive",
        "LMS Karras",
        "DPM2 Karras",
        "DPM2 a Karras",
        "DDIM",
        "PLMS",
    ],
    default="Euler",
    required=False,
)
@lightbulb.option(
    "height",
    "The height of the image.",
    type=int,
    min_value=64,
    max_value=2048,
    default=512,
    required=False,
)
@lightbulb.option(
    "width",
    "The weight of the image.",
    type=int,
    min_value=64,
    max_value=2048,
    default=512,
    required=False,
)
@lightbulb.option(
    "seed", "The seed to use to make the image.", type=int, default=-1, required=False
)
@lightbulb.option(
    "subseed",
    "An optional sub-seed to mix into the generation.",
    type=int,
    default=-1,
    required=False,
)
@lightbulb.option(
    "subseed_strength",
    "The strength to mix in the sub-seed.",
    type=int,
    default=0,
    required=False,
)
@lightbulb.option(
    "facefix",
    "Attempt to make faces look natural.",
    type=bool,
    default=False,
    required=False,
)
@lightbulb.option(
    "hrfix",
    "Attempt to make high resolutions.",
    type=bool,
    default=False,
    required=False,
)
@lightbulb.option("tiling", "Enable tiling.", type=bool, default=False, required=False)
@lightbulb.command("diffuse", "Run some stable diffusion.")
@lightbulb.implements(lightbulb.SlashCommand)
async def stable_diffuse(ctx: lightbulb.Context) -> None:

    resp = await ctx.respond(f"Let me create `{ctx.options.prompt}`", reply=True)
    message = await resp.message()

    payload = copy.deepcopy(REQUEST_TEMPLATE)
    payload["prompt"] = ctx.options.prompt
    payload["negative_prompt"] = ctx.options.negative_prompt
    payload["steps"] = ctx.options.steps
    payload["sampler_index"] = ctx.options.sampler
    payload["height"] = ctx.options.height
    payload["width"] = ctx.options.width
    payload["seed"] = ctx.options.seed
    payload["subseed"] = ctx.options.subseed
    payload["subseed_strength"] = ctx.options.subseed_strength
    payload["restore_faces"] = ctx.options.facefix
    payload["enable_hr"] = ctx.options.hrfix
    payload["tiling"] = ctx.options.tiling

    model = ctx.options.model
    session = get_aiohttp_client(ctx.bot)

    sd_server = config.STABLE_DIFFUSION_SERVERS[0]
    url = f"http://{sd_server.host}:{sd_server.port}"

    async def message_updater():
        while True:
            try:
                async with session.get(
                    url + StableDiffustionEndpoints.PROGRESS
                ) as progress_response:
                    r = await progress_response.json()
                    # if r["current_image"] is None:
                    #     waiting = False
                    #     break
                    await message.edit(
                        f"Let me create `{ctx.options.prompt}` `{int(abs(r['progress']) * 100)}%` - eta: `{int(abs(r['eta_relative']))}s`"
                    )

            except Exception as ex:
                logger.warning(ex)
            await asyncio.sleep(1.5)

    message_tasks[message.id] = asyncio.create_task(message_updater())

    try:
        async with session.post(
            url + StableDiffustionEndpoints.TEXT2IMG,
            json=payload,
            timeout=timedelta(days=1).total_seconds(),
        ) as response:
            r = await response.json()
            load_r = json.loads(r["info"])
            meta = load_r["infotexts"][0]

            for i in r["images"]:
                image = Image.open(io.BytesIO(base64.b64decode(i)))
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", meta)
                buf = io.BytesIO()
                image.save(buf, format="png", pnginfo=pnginfo)
                buf.seek(0)

                await ctx.respond(
                    f"Order's up! `{ctx.options.prompt}`",
                    attachment=hikari.Bytes(buf, f"stable_diffusion_{time.time()}.png"),
                )
    except Exception as ex:
        logger.exception(ex)
    finally:
        message_tasks[message.id].cancel()


def load(bot: lightbulb.BotApp) -> None:
    bot.add_plugin(ai_plugin)


def unload(bot: lightbulb.BotApp) -> None:
    bot.remove_plugin(ai_plugin)
