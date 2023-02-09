import asyncio
import base64
import copy
import io
import json
import logging
import time
from datetime import timedelta
from http import HTTPStatus
from typing import List, Optional

import aiohttp
import hikari
import lightbulb
from PIL import Image, PngImagePlugin

from beanbot import config

logger = logging.getLogger(__name__)

ai_plugin = lightbulb.Plugin(name="AI", description="Using ai to do things.")


class StableDiffustionEndpoints:
    LOGIN: str = "/login/"
    PREDICT: str = "/api/predict"
    SAMPLERS: str = "/sdapi/v1/samplers"
    MODELS: str = "/sdapi/v1/sd-models"
    PROGRESS: str = "/sdapi/v1/progress"
    TEXT2IMG: str = "/sdapi/v1/txt2img"
    IMG2IMG: str = "/sdapi/v1/img2img"


class Sampler:
    def __init__(self, name, aliases, options, *args, **kwargs) -> None:
        self.name = name
        self.aliases = (aliases,)
        self.options = options
        self.args = args
        self.kwargs = kwargs


class Model:
    def __init__(
        self, title, model_name, hash, filename, config, *args, **kwargs
    ) -> None:
        self.title = title
        self.model_name = model_name
        self.hash = hash
        self.filename = filename
        self.config = config
        self.args = args
        self.kwargs = kwargs


class Node:
    def __init__(
        self,
        hostname: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:
        self.__hostname = hostname
        self.__port = port
        self.__username = username
        self.__password = password

        self.__models: List[Model] = []
        self.__samplers: List[Sampler] = {}

        url = f"{hostname}:{port}"
        self.__session = aiohttp.ClientSession(url)

    @property
    def hostname(self):
        return self.__hostname

    @property
    def port(self):
        return self.__port

    @property
    def session(self):
        return self.__session

    @property
    def models(self):
        return self.__models

    @property
    def samplers(self):
        return self.__samplers

    async def get_models(self, refresh: bool = False) -> List[Model]:
        if self.models and not refresh:
            return self.models

        self.__models.clear()

        async with self.session.get(StableDiffustionEndpoints.MODELS) as response:
            if response.status != HTTPStatus.OK:
                logger.warning(f"get models returns bad status! {response.status}")

            self.__models.extend([Model(**item) for item in await response.json()])
            return self.models

    async def get_samplers(self, refresh: bool = False) -> List[Sampler]:
        if self.samplers and not refresh:
            return self.samplers

        self.__samplers.clear()

        async with self.session.get(StableDiffustionEndpoints.SAMPLERS) as response:
            if response.status != HTTPStatus.OK:
                logger.warning(f"get samplers returns bad status! {response.status}")

            self.__samplers.extend([Sampler(**item) for item in await response.json()])

            return self.samplers

    async def get_progress(self):
        async with self.session.get(StableDiffustionEndpoints.PROGRESS) as response:
            if response.status != HTTPStatus.OK:
                logger.warning(f"get progress returns bad status! {response.status}")

            return await response.json()

    def __eq__(self, __o: object) -> bool:
        return (
            isinstance(__o, Node)
            and self.hostname == __o.hostname
            and self.port == __o.port
        )

    def __hash__(self) -> int:
        pass


class Client:
    def __init__(self) -> None:
        self.__nodes: List[Node] = []
        self.__availible_models = dict[str, List[Node]] = {}
        self.__availible_samplers = dict[str, List[Node]] = {}

    @property
    def nodes(self) -> List[Node]:
        return self.__nodes

    @property
    def availible_models(self) -> List[str]:
        return list(self.__availible_models.keys())

    @property
    def availible_samplers(self) -> List[str]:
        return list(self.__availible_samplers.keys())

    async def add_node(
        self,
        hostname: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ) -> None:

        new_node = Node(hostname, port, username, password)

        for node in self.nodes:
            if node == new_node:
                return

        self.__nodes.append(new_node)
        await self.update_attrs(new_node)

    async def update_attrs(self, node: Node):
        models = await node.get_models(True)
        samplers = await node.get_samplers(True)

        for model in models:
            nodes_with_model = self.__availible_models.get(model.model_name, [])
            nodes_with_model.append(node)
            nodes_with_model = list(set(nodes_with_model))
            self.__availible_models.update({model.model_name: nodes_with_model})

        for sampler in samplers:
            nodes_with_sampler = self.__availible_samplers.get(sampler.name, [])
            nodes_with_sampler.append(node)
            nodes_with_sampler = list(set(nodes_with_sampler))
            self.__availible_samplers.update({sampler.name: nodes_with_sampler})

    async def refresh_all_attrs(self):
        self.__availible_models.clear()
        self.__availible_samplers.clear()

        for node in self.nodes:
            await self.update_attrs(node)

    async def get_node(self, model: str = None, sampler: str = None):
        pass


LOGIN_TEMPLATE = {"username": "", "password": ""}

MODEL_CHANGE_TEMPLATE = {"fn_index": 0, "data": [""]}

# IMG_TEMPLATE = {
#     "prompt": queue_object.prompt,
#     "negative_prompt": queue_object.negative_prompt,
#     "steps": queue_object.steps,
#     "height": queue_object.height,
#     "width": queue_object.width,
#     "cfg_scale": queue_object.guidance_scale,
#     "sampler_index": queue_object.sampler,
#     "seed": queue_object.seed,
#     "seed_resize_from_h": 0,
#     "seed_resize_from_w": 0,
#     "denoising_strength": None,
#     "n_iter": queue_object.batch_count,
#     "styles": [
#         queue_object.style
#     ]
# }

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

# image = base64.b64encode(requests.get(queue_object.init_image.url, stream=True).content).decode('utf-8')
INIT_IMAGE_TEMPLATE = {
    "init_images": ["data:image/png;base64," + "base 64 encoded image"],
    "denoising_strength": 0,
}

FACE_FIX_SETTINGS_TEMPLATE = {"face_restoration_model": ""}


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
    default=20,
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
@lightbulb.command("diffuse", "Create images.")
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
