# Daisyxmusic (Telegram bot project)
# Copyright (C) 2021  Inukaasith
# Copyright (C) 2021  TheHamkerCat (Python_ARQ)
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


import json
import os
from os import path
from typing import Callable

import aiofiles
import aiohttp
import ffmpeg
import requests
import wget
from PIL import Image
from PIL import ImageDraw
from PIL import ImageFont
from pyrogram import Client
from pyrogram import filters
from pyrogram.types import Voice
from pyrogram.errors import UserAlreadyParticipant
from pyrogram.types import InlineKeyboardButton
from pyrogram.types import InlineKeyboardMarkup
from pyrogram.types import Message
from Python_ARQ import ARQ
from youtube_search import YoutubeSearch

from DaisyXMusic.config import ARQ_API_KEY
from DaisyXMusic.config import BOT_NAME as bn
from DaisyXMusic.config import DURATION_LIMIT
from DaisyXMusic.config import UPDATES_CHANNEL as updateschannel
from DaisyXMusic.config import que
from DaisyXMusic.function.admins import admins as a
from DaisyXMusic.helpers.admins import get_administrators
from DaisyXMusic.helpers.channelmusic import get_chat_id
from DaisyXMusic.helpers.errors import MüddətiLimitError
from DaisyXMusic.helpers.decorators import errors
from DaisyXMusic.helpers.decorators import authorized_users_only
from DaisyXMusic.helpers.filters import command
from DaisyXMusic.helpers.filters import other_filters
from DaisyXMusic.helpers.gets import get_file_name
from DaisyXMusic.services.callsmusic import callsmusic
from DaisyXMusic.services.callsmusic import client as USER
from DaisyXMusic.services.converter.converter import convert
from DaisyXMusic.services.downloaders import youtube
from DaisyXMusic.services.queues import queues

aiohttpsession = aiohttp.ClientSession()
chat_id = None
arq = ARQ("https://thearq.tech", ARQ_API_KEY, aiohttpsession)
DISABLED_GROUPS = []
useer ="NaN"
def cb_admin_check(func: Callable) -> Callable:
    async def decorator(client, cb):
        admemes = a.get(cb.message.chat.id)
        if cb.from_user.id in admemes:
            return await func(client, cb)
        else:
            await cb.answer("You ain't allowed!", show_alert=True)
            return

    return decorator


def transcode(filename):
    ffmpeg.input(filename).output(
        "input.raw", 
        format="s16le", 
        acodec="pcm_s16le", 
        ac=2, 
        ar="48k"
    ).overwrite_output().run()
    os.remove(filename)


# Convert seconds to mm:ss
def convert_seconds(seconds):
    seconds = seconds % (24 * 3600)
    seconds %= 3600
    minutes = seconds // 60
    seconds %= 60
    return "%02d:%02d" % (minutes, seconds)


# Convert hh:mm:ss to seconds
def time_to_seconds(time):
    stringt = str(time)
    return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))


# Change image size
def changeImageSize(maxWidth, maxHeight, image):
    widthRatio = maxWidth / image.size[0]
    heightRatio = maxHeight / image.size[1]
    newWidth = int(widthRatio * image.size[0])
    newHeight = int(heightRatio * image.size[1])
    newImage = image.resize((newWidth, newHeight))
    return newImage


async def generate_cover(requested_by, title, views, duration, thumbnail):
    async with aiohttp.ClientSession() as session:
        async with session.get(thumbnail) as resp:
            if resp.status == 200:
                f = await aiofiles.open("background.png", mode="wb")
                await f.write(await resp.read())
                await f.close()

    image1 = Image.open("./background.png")
    image2 = Image.open("./etc/foreground.png")
    image3 = changeImageSize(1280, 720, image1)
    image4 = changeImageSize(1280, 720, image2)
    image5 = image3.convert("RGBA")
    image6 = image4.convert("RGBA")
    Image.alpha_composite(image5, image6).save("temp.png")
    img = Image.open("temp.png")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("etc/font.otf", 32)
    draw.text((205, 550), f"Adı: {title}", (51, 215, 255), font=font)
    draw.text((205, 590), f"Musiqi vaxyı: {duration}", (255, 255, 255), font=font)
    draw.text((205, 630), f"Baxış sayı: {views}", (255, 255, 255), font=font)
    draw.text(
        (205, 670),
        f"Added By: {requested_by}",
        (255, 255, 255),
        font=font,
    )
    img.save("final.png")
    os.remove("temp.png")
    os.remove("background.png")


@Client.on_message(filters.command("playlist") & filters.group & ~filters.edited)
async def playlist(client, message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return    
    queue = que.get(message.chat.id)
    if not queue:
        await message.reply_text("Player is idle")
    temp = []
    for t in queue:
        temp.append(t)
    now_playing = temp[0][0]
    by = temp[0][1].mention(style="md")
    msg = "**Hal hazırda ifa olunur** {}".format(message.chat.title)
    msg += "\n- " + now_playing
    msg += by + "\n- tərəfindən "
    temp.pop(0)
    if temp:
        msg += "\n\n"
        msg += "**Növbədəki**"
        for song in temp:
            name = song[0]
            usr = song[1].mention(style="md")
            msg += f"\n- {name}"
            msg += f"\n- {usr} tərəfindən.\n"
    await message.reply_text(msg)


# ============================= Settings =========================================


def updated_stats(chat, queue, vol=100):
    if chat.id in callsmusic.active_chats:
        # if chat.id in active_chats:
        stats = "Settings of **{}**".format(chat.title)
        if len(que) > 0:
            stats += "\n\n"
            stats += "Həcmi (Volume) : {}%\n".format(vol)
            stats += "Gözləmədə olan `{}` musiqi var. \n".format(len(que))
            stats += "Hal hazırda ifa olunan musiqi : **{}**\n".format(queue[0][0])
            stats += "{} tərəfindən musiqi qoşuldu.".format(queue[0][1].mention)
    else:
        stats = None
    return stats


def r_ply(type_):
    if type_ == "play":
        pass
    else:
        pass
    mar = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("⏹", "leave"),
                InlineKeyboardButton("⏸", "puse"),
                InlineKeyboardButton("▶️", "resume"),
                InlineKeyboardButton("⏭", "skip"),
            ],
            [
                InlineKeyboardButton("Playlist 📖", "playlist"),
            ],
            [InlineKeyboardButton("❌ Bağla", "cls")],
        ]
    )
    return mar


@Client.on_message(filters.command("current") & filters.group & ~filters.edited)
async def ee(client, message):
    if message.chat.id in DISABLED_GROUPS:
        return
    queue = que.get(message.chat.id)
    stats = updated_stats(message.chat, queue)
    if stats:
        await message.reply(stats)
    else:
        await message.reply("Bu söhbətdə çalışan VC nümunələri yoxdur")


@Client.on_message(filters.command("player") & filters.group & ~filters.edited)
@authorized_users_only
async def settings(client, message):
    if message.chat.id in DISABLED_GROUPS:
        await message.reply("Music Player deaktiv olunub.")
        return    
    playing = None
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.active_chats:
        playing = True
    queue = que.get(chat_id)
    stats = updated_stats(message.chat, queue)
    if stats:
        if playing:
            await message.reply(stats, reply_markup=r_ply("pause")) 
        else:
            await message.reply(stats, reply_markup=r_ply("play"))
    else:
        await message.reply("Bu söhbətdə çalışan VC nümunələri yoxdur")


@Client.on_message(
    filters.command("musicplayer") & ~filters.edited & ~filters.bot & ~filters.private
)
@authorized_users_only
async def hfmm(_, message):
    global DISABLED_GROUPS
    try:
        user_id = message.from_user.id
    except:
        return
    if len(message.command) != 2:
        await message.reply_text(
            "Yalnız `/musicplayer on` və /musicplayer `off only` yaza bilərsiniz."
        )
        return
    status = message.text.split(None, 1)[1]
    message.chat.id
    if status == "ON" or status == "on" or status == "On":
        lel = await message.reply("`Hazırlanır...`")
        if not message.chat.id in DISABLED_GROUPS:
            await lel.edit("Bu Çatda Musiqi Pleyeri artıq aktivdir")
            return
        DISABLED_GROUPS.remove(message.chat.id)
        await lel.edit(
            f"Musiqi pleyeri aktiv olundu. CHATID: {message.chat.id}"
        )

    elif status == "OFF" or status == "off" or status == "Off":
        lel = await message.reply("`Hazırlanır...`")
        
        if message.chat.id in DISABLED_GROUPS:
            await lel.edit("Bu Çatda Musiqi Pleyeri artıq söndürülüb")
            return
        DISABLED_GROUPS.append(message.chat.id)
        await lel.edit(
            f"Musiqi pleyeri deaktiv olundu. CHATID:  {message.chat.id}"
        )
    else:
        await message.reply_text(
            "I only recognize `/musicplayer on` and /musicplayer `off only`"
        )    
        

@Client.on_callback_query(filters.regex(pattern=r"^(playlist)$"))
async def p_cb(b, cb):
    global que
    que.get(cb.message.chat.id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    cb.message.chat
    cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("Player is idle")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "<b>Hal hazırda oxunur </b>  {}".format(cb.message.chat.title)
        msg += "\n- " + now_playing
        msg += by + "\n- tərəfindən "
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Növbədəki**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- {usr} tərəfindən.\n"
        await cb.message.edit(msg)


@Client.on_callback_query(
    filters.regex(pattern=r"^(play|pause|skip|leave|puse|resume|menu|cls)$")
)
@cb_admin_check
async def m_cb(b, cb):
    global que
    if (
        cb.message.chat.title.startswith("Kanal Music: ")
        and chat.title[14:].isnumeric()
    ):
        chet_id = int(chat.title[13:])
    else:
        chet_id = cb.message.chat.id
    qeue = que.get(chet_id)
    type_ = cb.matches[0].group(1)
    cb.message.chat.id
    m_chat = cb.message.chat

    the_data = cb.message.reply_markup.inline_keyboard[1][0].callback_data
    if type_ == "pause":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "paused"
        ):
            await cb.answer("Çat bağlı deyil!", show_alert=True)
        else:
            callsmusic.pause(chet_id)
            await cb.answer("Musiqi dayandırıldı!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("play")
            )

    elif type_ == "play":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "playing"
        ):
            await cb.answer("Çat bağlı deyil!", show_alert=True)
        else:
            callsmusic.resume(chet_id)
            await cb.answer("Musiqi davam edir!")
            await cb.message.edit(
                updated_stats(m_chat, qeue), reply_markup=r_ply("pause")
            )

    elif type_ == "playlist":
        queue = que.get(cb.message.chat.id)
        if not queue:
            await cb.message.edit("Player is idle")
        temp = []
        for t in queue:
            temp.append(t)
        now_playing = temp[0][0]
        by = temp[0][1].mention(style="md")
        msg = "**Now Oxunur** in {}".format(cb.message.chat.title)
        msg += "\n- " + now_playing
        msg += by + "\n- tərəfindən "
        temp.pop(0)
        if temp:
            msg += "\n\n"
            msg += "**Növbədəki**"
            for song in temp:
                name = song[0]
                usr = song[1].mention(style="md")
                msg += f"\n- {name}"
                msg += f"\n- {usr} tərəfindən.\n"
        await cb.message.edit(msg)

    elif type_ == "resume":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "playing"
        ):
            await cb.answer("Çat bağlı deyil və ya artıq səsləndirilir", show_alert=True)
        else:
            callsmusic.resume(chet_id)
            await cb.answer("Musiqi davam edir!")
    elif type_ == "puse":
        if (chet_id not in callsmusic.active_chats) or (
            callsmusic.active_chats[chet_id] == "paused"
        ):
            await cb.answer("Çat bağlı deyil və ya artıq dayandırılıb", show_alert=True)
        else:
            callsmusic.pause(chet_id)
            await cb.answer("Musiqi dayandırıldı!")
    elif type_ == "cls":
        await cb.answer("Menyunu bağla")
        await cb.message.delete()

    elif type_ == "menu":
        stats = updated_stats(cb.message.chat, qeue)
        await cb.answer("Menu opened")
        marr = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⏹", "leave"),
                    InlineKeyboardButton("⏸", "puse"),
                    InlineKeyboardButton("▶️", "resume"),
                    InlineKeyboardButton("⏭", "skip"),
                ],
                [
                    InlineKeyboardButton("Playlist 📖", "playlist"),
                ],
                [InlineKeyboardButton("❌ Bağla", "cls")],
            ]
        )
        await cb.message.edit(stats, reply_markup=marr)
    elif type_ == "skip":
        if qeue:
            qeue.pop(0)
        if chet_id not in callsmusic.active_chats:
            await cb.answer("Çat bağlı deyil!", show_alert=True)
        else:
            queues.task_done(chet_id)
            if queues.is_empty(chet_id):
                callsmusic.stop(chet_id)
                await cb.message.edit("- Musiqi bitdi. \n Səsli söhbətdən çıxıram.")
            else:
                await callsmusic.set_stream(
                    chet_id, queues.get(chet_id)["file"]
                )
                await cb.answer.reply_text("✅ <b>Növbəti musiqiyə keçdi.</b>")
                await cb.message.edit((m_chat, qeue), reply_markup=r_ply(the_data))
                await cb.message.reply_text(
                    f"- Növbəti musiqiyə keçdi.\n- Hal hazırda oxunur **{qeue[0][0]}**"
                )

    else:
        if chet_id in callsmusic.active_chats:
            try:
               queues.clear(chet_id)
            except NövbədəkiEmpty:
                pass

            await callsmusic.stop(chet_id)
            await cb.message.edit("Uğurla qrupdan çıxarıldı.")
        else:
            await cb.answer("Çat bağlı deyil!", show_alert=True)


@Client.on_message(command("play") & other_filters)
async def play(_, message: Message):
    global que
    global useer
    if message.chat.id in DISABLED_GROUPS:
        return    
    lel = await message.reply("🔄 <b>Hazırlanır</b>")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id

    try:
        user = await USER.get_me()
    except:
        user.first_name = "helper"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Kanal musiqisi: "):
                    await lel.edit(
                        "<b>Kanalınıza köməkçi əlavə etməyi unutmayın</b>",
                    )
                    pass
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Məni ilk oncə admin olaraq əlavə edin.</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "Userbot qrupa qoşuldu."
                    )
                    await lel.edit(
                        "<b>Userbot qrupa qoşuldu.</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Flood gözləmə xətası 🔴 \n{user.first_name}, bot həddindən çox qrupda məşğul olduğu üçün səsli söhbətə qoşula bilmədi! Və ya userbot(səsli söhbətə qoşulan musiqi plugini)-un qrupda ban olunmadığına əmin olun."
                        "\n\nƏgər yuxarıdakılardan heç biri işinizə yaramadısa botu əl ilə qrupa əlavə edin və ya @UhuMusicSupport -a daxil olub dəstək istəyin.</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i> {user.first_name} Userbot bu söhbətdə deyil, Admindən ilk dəfə əmr göndərməsini və ya {user.first_name}-i əlavə etməsini istəyin.</i>"
        )
        return
    text_links=None
    await lel.edit("🔎 <b>Axtarılır</b>")
    if message.reply_to_message:
        if message.reply_to_message.audio:
            pass
        entities = []
        toxt = message.reply_to_message.text \
              or message.reply_to_message.caption
        if message.reply_to_message.entities:
            entities = message.reply_to_message.entities + entities
        elif message.reply_to_message.caption_entities:
            entities = message.reply_to_message.entities + entities
        urls = [entity for entity in entities if entity.type == 'url']
        text_links = [
            entity for entity in entities if entity.type == 'text_link'
        ]
    else:
        urls=None
    if text_links:
        urls = True
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    rpk = "[" + user_name + "](tg://user?id=" + str(user_id) + ")"
    audio = (
        (message.reply_to_message.audio or message.reply_to_message.voice)
        if message.reply_to_message
        else None
    )
    if audio:
        if round(audio.duration / 60) > DURATION_LIMIT:
            await lel.edit(
                f"❌ Video {DURATION_LIMIT} dəqiqədən uzun olduğu üçün musiqi ifa olunmur!"
            )
            return
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📖 Pleylist", callback_data="playlist"),
                    InlineKeyboardButton("Menyu ⏯ ", callback_data="menu"),
                ],
                [InlineKeyboardButton(text="❌ Bağla", callback_data="cls")],
            ]
        )
        file_name = get_file_name(audio)
        title = file_name
        thumb_name = "https://telegra.ph/file/f6086f8909fbfeb0844f2.png"
        thumbnail = thumb_name
        duration = round(audio.duration / 60)
        views = "Locally added"
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await convert(
            (await message.reply_to_message.download(file_name))
            if not path.isfile(path.join("downloads", file_name))
            else file_name
        )
    elif urls:
        query = toxt
        await lel.edit("🎵 <b>Hazırlanır</b>")
        ydl_opts = {"format": "bestaudio/best"}
        try:
            results = YoutubeSearch(query, max_results=1).to_dict()
            url = f"https://youtube.com{results[0]['url_suffix']}"
            # print(results)
            title = results[0]["title"][:40]
            thumbnail = results[0]["thumbnails"][0]
            thumb_name = f"thumb{title}.jpg"
            thumb = requests.get(thumbnail, allow_redirects=True)
            open(thumb_name, "wb").write(thumb.content)
            duration = results[0]["duration"]
            results[0]["url_suffix"]
            views = results[0]["views"]

        except Exception as e:
            await lel.edit(
                "Musiqi tapılmadı. Başqa musiqi yoxlayın :/."
            )
            print(str(e))
            return
        try:    
            secmul, dur, dur_arr = 1, 0, duration.split(':')
            for i in range(len(dur_arr)-1, -1, -1):
                dur += (int(dur_arr[i]) * secmul)
                secmul *= 60
            if (dur / 60) > DURATION_LIMIT:
                 await lel.edit(f"❌ Video {DURATION_LIMIT} dəqiqədən uzun olduğu üçün musiqi ifa olunmur!")
                 return
        except:
            pass        
        dlurl=url
        dlurl=dlurl.replace("youtube","youtubepp")
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("📖 Pleylist", callback_data="playlist"),
                    InlineKeyboardButton("Menyu ⏯ ", callback_data="menu"),
                ],
                [
                    InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                    InlineKeyboardButton(text="Yüklə 📥", url=f"{dlurl}"),
                ],
                [InlineKeyboardButton(text="❌ Bağla", callback_data="cls")],
            ]
        )
        requested_by = message.from_user.first_name
        await generate_cover(requested_by, title, views, duration, thumbnail)
        file_path = await convert(youtube.download(url))        
    else:
        query = ""
        for i in message.command[1:]:
            query += " " + str(i)
        print(query)
        await lel.edit("🎵 **Hazırlanır**")
        ydl_opts = {"format": "bestaudio/best"}
        
        try:
          results = YoutubeSearch(query, max_results=5).to_dict()
        except:
          await lel.edit("Musiqi ifa olunması üçün bir şey qeyd edin.")
        # Looks like hell. Aren't it?? FUCK OFF
        try:
            toxxt = "**Oxutmaq istədiyiniz musiqini seçin:**\n\n"
            j = 0
            useer=user_name
            emojilist = ["1️⃣","2️⃣","3️⃣","4️⃣","5️⃣",]

            while j < 5:
                toxxt += f"{emojilist[j]} <b>Adı - [{results[j]['title']}](https://youtube.com{results[j]['url_suffix']})</b>\n"
                toxxt += f" ╚ <b>Müddəti</b> - {results[j]['duration']}\n"
                toxxt += f" ╚ <b>Baxış sayı</b> - {results[j]['views']}\n"
                toxxt += f" ╚ <b>Kanal</b> - {results[j]['channel']}\n\n"

                j += 1            
            koyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("1️⃣", callback_data=f'plll 0|{query}|{user_id}'),
                        InlineKeyboardButton("2️⃣", callback_data=f'plll 1|{query}|{user_id}'),
                        InlineKeyboardButton("3️⃣", callback_data=f'plll 2|{query}|{user_id}'),
                    ],
                    [
                        InlineKeyboardButton("4️⃣", callback_data=f'plll 3|{query}|{user_id}'),
                        InlineKeyboardButton("5️⃣", callback_data=f'plll 4|{query}|{user_id}'),
                    ],
                    [InlineKeyboardButton(text="❌", callback_data="cls")],
                ]
            )       
            await lel.edit(toxxt,reply_markup=koyboard,disable_web_page_preview=True)
            # WHY PEOPLE ALWAYS LOVE PORN ?? (A point to think)
            return
            # Returning to pornhub
        except:
            await lel.edit("Yalnız 1 musiqi tapıldığı üçün birbaşa musiqi oxunmağa başlayır...")
                        
            # print(results)
            try:
                url = f"https://youtube.com{results[0]['url_suffix']}"
                title = results[0]["title"][:40]
                thumbnail = results[0]["thumbnails"][0]
                thumb_name = f"thumb{title}.jpg"
                thumb = requests.get(thumbnail, allow_redirects=True)
                open(thumb_name, "wb").write(thumb.content)
                duration = results[0]["duration"]
                results[0]["url_suffix"]
                views = results[0]["views"]

            except Exception as e:
                await lel.edit(
                    "Musiqi tapılmadı. Başqa musiqi yoxlayın :/."
                )
                print(str(e))
                return
            try:    
                secmul, dur, dur_arr = 1, 0, duration.split(':')
                for i in range(len(dur_arr)-1, -1, -1):
                    dur += (int(dur_arr[i]) * secmul)
                    secmul *= 60
                if (dur / 60) > DURATION_LIMIT:
                     await lel.edit(f"❌ Video {DURATION_LIMIT} dəqiqədən uzun olduğu üçün musiqi ifa olunmur!")
                     return
            except:
                pass
            dlurl=url
            dlurl=dlurl.replace("youtube","youtubepp")
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("📖 Pleylist", callback_data="playlist"),
                        InlineKeyboardButton("Menyu ⏯ ", callback_data="menu"),
                    ],
                    [
                        InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                        InlineKeyboardButton(text="Yüklə 📥", url=f"{dlurl}"),
                    ],
                    [InlineKeyboardButton(text="❌ Bağla", callback_data="cls")],
                ]
            )
            requested_by = message.from_user.first_name
            await generate_cover(requested_by, title, views, duration, thumbnail)
            file_path = await convert(youtube.download(url))   
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"#⃣ İstədiyiniz mahnı <b>sıraya qoyuldu/b>. Sırası: {position}!",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        return await lel.delete()
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            await callsmusic.set_stream(chat_id, file_path)
        except:
            message.reply("Qrup zəngi açılmayıb və ya mən qoşula bilmirəm.")
            return
        await message.reply_photo(
            photo="final.png",
            reply_markup=keyboard,
            caption="▶️ <b>Oxunur...</b> Musiqini oxudan şəxs: {}. Youtube Music vasitəsi ilə qoşuldu 😎".format(
                message.from_user.mention()
            ),
        )
        os.remove("final.png")
        return await lel.delete()


@Client.on_message(filters.command("ytplay") & filters.group & ~filters.edited)
async def ytplay(_, message: Message):
    global que
    if message.chat.id in DISABLED_GROUPS:
        return
    lel = await message.reply("🔄 <b>Hazırlanır</b>")
    administrators = await get_administrators(message.chat)
    chid = message.chat.id

    try:
        user = await USER.get_me()
    except:
        user.first_name = "helper"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await _.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message.from_user.id:
                if message.chat.title.startswith("Kanal Music: "):
                    await lel.edit(
                        "<b>Kanalınıza köməkçi əlavə etməyi unutmayın</b>",
                    )
                    pass
                try:
                    invitelink = await _.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Məni ilk oncə admin olaraq əlavə edin.</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message.chat.id, "Userbot qrupa qoşuldu."
                    )
                    await lel.edit(
                        "<b>Userbot qrupa qoşuldu.</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Flood gözləmə xətası 🔴 \n{user.first_name}, bot həddindən çox qrupda məşğul olduğu üçün səsli söhbətə qoşula bilmədi! Və ya userbot(səsli söhbətə qoşulan musiqi plugini)-un qrupda ban olunmadığına əmin olun."
                        "\n\nƏgər yuxarıdakılardan heç biri işinizə yaramadısa botu əl ilə qrupa əlavə edin və ya @UhuMusicSupport -a daxil olub dəstək istəyin.</b>",
                    )

    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            f"<i> {user.first_name}, Userbot qrupda yoxdu manual olaraq əlavə etməyi yoxlayın.</i>"
        )
        return
    await lel.edit("🔎 <b>Axtarılır</b>")
    user_id = message.from_user.id
    user_name = message.from_user.first_name
     

    query = ""
    for i in message.command[1:]:
        query += " " + str(i)
    print(query)
    await lel.edit("🎵 <b>Hazırlanır</b>")
    ydl_opts = {"format": "bestaudio/best"}
    try:
        results = YoutubeSearch(query, max_results=1).to_dict()
        url = f"https://youtube.com{results[0]['url_suffix']}"
        # print(results)
        title = results[0]["title"][:40]
        thumbnail = results[0]["thumbnails"][0]
        thumb_name = f"thumb{title}.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
        duration = results[0]["duration"]
        results[0]["url_suffix"]
        views = results[0]["views"]

    except Exception as e:
        await lel.edit(
            "Musiqi tapılmadı. Başqa musiqi yoxlayın :/."
        )
        print(str(e))
        return
    try:    
        secmul, dur, dur_arr = 1, 0, duration.split(':')
        for i in range(len(dur_arr)-1, -1, -1):
            dur += (int(dur_arr[i]) * secmul)
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
             await lel.edit(f"❌ Video {DURATION_LIMIT} dəqiqədən uzun olduğu üçün musiqi ifa olunmur!")
             return
    except:
        pass    
    dlurl=url
    dlurl=dlurl.replace("youtube","youtubepp")
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Pleylist", callback_data="playlist"),
                InlineKeyboardButton("Menyu ⏯ ", callback_data="menu"),
            ],
            [
                InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                InlineKeyboardButton(text="Yüklə 📥", url=f"{dlurl}"),
            ],
            [InlineKeyboardButton(text="❌ Bağla", callback_data="cls")],
        ]
    )
    requested_by = message.from_user.first_name
    await generate_cover(requested_by, title, views, duration, thumbnail)
    file_path = await convert(youtube.download(url))
    chat_id = get_chat_id(message.chat)
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await message.reply_photo(
            photo="final.png",
            caption=f"#⃣ İstədiyiniz musiqi <b>sıraya alındı.</b> sıra nömrəsi:{position}!",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        return await lel.delete()
    else:
        chat_id = get_chat_id(message.chat)
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        r_by = message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
           await callsmusic.set_stream(chat_id, file_path)
        except:
            message.reply("Səsli söhbət yoxdur və ya mən qoşula bilmirəm.")
            return
        await message.reply_photo(
            photo="final.png",
            reply_markup=keyboard,
            caption="▶️ <b>Oxunur...</b> Musiqini oxudan şəxs: {}. Youtube Music vasitəsi ilə qoşuldu 😎".format(
                message.from_user.mention()
            ),
        )
        os.remove("final.png")
        return await lel.delete()
    

@Client.on_message(filters.command("splay") & filters.group & ~filters.edited)
async def jiosaavn(client: Client, message_: Message):
    global que
    if message_.chat.id in DISABLED_GROUPS:
        return    
    lel = await message_.reply("🔄 <b>Hazırlanır</b>")
    administrators = await get_administrators(message_.chat)
    chid = message_.chat.id
    try:
        user = await USER.get_me()
    except:
        user.first_name = "UhuMusic"
    usar = user
    wew = usar.id
    try:
        # chatdetails = await USER.get_chat(chid)
        await client.get_chat_member(chid, wew)
    except:
        for administrator in administrators:
            if administrator == message_.from_user.id:
                if message_.chat.title.startswith("Kanal Music: "):
                    await lel.edit(
                        "<b>Kanalınıza köməkçi əlavə etməyi unutmayın</b>",
                    )
                    pass
                try:
                    invitelink = await client.export_chat_invite_link(chid)
                except:
                    await lel.edit(
                        "<b>Məni ilk oncə admin olaraq əlavə edin.</b>",
                    )
                    return

                try:
                    await USER.join_chat(invitelink)
                    await USER.send_message(
                        message_.chat.id, "Userbot qrupa qoşuldu."
                    )
                    await lel.edit(
                        "<b>Userbot qrupa qoşuldu.</b>",
                    )

                except UserAlreadyParticipant:
                    pass
                except Exception:
                    # print(e)
                    await lel.edit(
                        f"<b>🔴 Flood gözləmə xətası 🔴 \n{user.first_name}, bot həddindən çox qrupda məşğul olduğu üçün səsli söhbətə qoşula bilmədi! Və ya userbot(səsli söhbətə qoşulan musiqi plugini)-un qrupda ban olunmadığına əmin olun."
                        "\n\nƏgər yuxarıdakılardan heç biri işinizə yaramadısa botu əl ilə qrupa əlavə edin və ya @UhuMusicSupport -a daxil olub dəstək istəyin.</b>",
                    )
    try:
        await USER.get_chat(chid)
        # lmoa = await client.get_chat_member(chid,wew)
    except:
        await lel.edit(
            "<i> köməkçi Userbot bu söhbətdə deyil, Admindən ilk dəfə əmr göndərməsini (/play) və ya köməkçini əl ilə əlavə etməsini xahiş et</i>"
        )
        return
    requested_by = message_.from_user.first_name
    chat_id = message_.chat.id
    text = message_.text.split(" ", 1)
    query = text[1]
    res = lel
    await res.edit(f"Searching 🔍 for `{query}` on jio saavn")
    try:
        songs = await arq.saavn(query)
        if not songs.ok:
            await message_.reply_text(songs.result)
            return
        sname = songs.result[0].song
        slink = songs.result[0].media_url
        ssingers = songs.result[0].singers
        sthumb = songs.result[0].image
        sduration = int(songs.result[0].duration)
    except Exception as e:
        await res.edit("Found Literally Nothing!, You Should Work On Your English.")
        print(str(e))
        return
    try:    
        duuration= round(sduration / 60)
        if duuration > DURATION_LIMIT:
            await cb.message.edit(f"Music longer than {DURATION_LIMIT}min are not allowed to play")
            return
    except:
        pass    
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Pleylist", callback_data="playlist"),
                InlineKeyboardButton("Menyu ⏯ ", callback_data="menu"),
            ],
            [
                InlineKeyboardButton(
                    text="Join Updates Kanal", url=f"https://t.me/{updateschannel}"
                )
            ],
            [InlineKeyboardButton(text="❌ Bağla", callback_data="cls")],
        ]
    )
    file_path = await convert(wget.download(slink))
    chat_id = get_chat_id(message_.chat)
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = sname
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await res.delete()
        m = await client.send_photo(
            chat_id=message_.chat.id,
            reply_markup=keyboard,
            photo="final.png",
            caption=f"✯{bn}✯=#️⃣ Növbədəki : {position}",
        )

    else:
        await res.edit_text(f"{bn}=▶️ Oxunur.....")
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = sname
        r_by = message_.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        try:
            await callsmusic.set_stream(chat_id, file_path)
        except:
            res.edit("Səsli söhbət tapılmadı və ya mən qoşula bilmirəm.")
            return
    await res.edit("Thumbnail hazırlanır.")
    await generate_cover(requested_by, sname, ssingers, sduration, sthumb)
    await res.delete()
    m = await client.send_photo(
        chat_id=message_.chat.id,
        reply_markup=keyboard,
        photo="final.png",
        caption=f"Oxunur {sname} Via Jiosaavn",
    )
    os.remove("final.png")


@Client.on_callback_query(filters.regex(pattern=r"plll"))
async def lol_cb(b, cb):
    global que

    cbd = cb.data.strip()
    chat_id = cb.message.chat.id
    typed_=cbd.split(None, 1)[1]
    #useer_id = cb.message.reply_to_message.from_user.id
    try:
        x,query,useer_id = typed_.split("|")      
    except:
        await cb.message.edit("Song Not Found")
        return
    useer_id = int(useer_id)
    if cb.from_user.id != useer_id:
        await cb.answer("You ain't the person who requested to play the song!", show_alert=True)
        return
    await cb.message.edit("Hang On... Player Starting")
    x=int(x)
    try:
        useer_name = cb.message.reply_to_message.from_user.first_name
    except:
        useer_name = cb.message.from_user.first_name
    
    results = YoutubeSearch(query, max_results=5).to_dict()
    resultss=results[x]["url_suffix"]
    title=results[x]["title"][:40]
    thumbnail=results[x]["thumbnails"][0]
    duration=results[x]["duration"]
    views=results[x]["views"]
    url = f"https://youtube.com{resultss}"
    
    try:    
        secmul, dur, dur_arr = 1, 0, duration.split(':')
        for i in range(len(dur_arr)-1, -1, -1):
            dur += (int(dur_arr[i]) * secmul)
            secmul *= 60
        if (dur / 60) > DURATION_LIMIT:
             await cb.message.edit(f"Music longer than {DURATION_LIMIT}min are not allowed to play")
             return
    except:
        pass
    try:
        thumb_name = f"thumb{title}.jpg"
        thumb = requests.get(thumbnail, allow_redirects=True)
        open(thumb_name, "wb").write(thumb.content)
    except Exception as e:
        print(e)
        return
    dlurl=url
    dlurl=dlurl.replace("youtube","youtubepp")
    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("📖 Pleylist", callback_data="playlist"),
                InlineKeyboardButton("Menyu ⏯ ", callback_data="menu"),
            ],
            [
                InlineKeyboardButton(text="🎬 YouTube", url=f"{url}"),
                InlineKeyboardButton(text="Yüklə 📥", url=f"{dlurl}"),
            ],
            [InlineKeyboardButton(text="❌ Bağla", callback_data="cls")],
        ]
    )
    requested_by = useer_name
    await generate_cover(requested_by, title, views, duration, thumbnail)
    file_path = await convert(youtube.download(url))  
    if chat_id in callsmusic.active_chats:
        position = await queues.put(chat_id, file=file_path)
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
        await cb.message.delete()
        await b.send_photo(chat_id,
            photo="final.png",
            caption=f"#⃣  Musiqi {r_by.mention} tərəfindən <b>sıraya alındı</b>. sıra nömrəsi {position}!",
            reply_markup=keyboard,
        )
        os.remove("final.png")
        
    else:
        que[chat_id] = []
        qeue = que.get(chat_id)
        s_name = title
        try:
            r_by = cb.message.reply_to_message.from_user
        except:
            r_by = cb.message.from_user
        loc = file_path
        appendable = [s_name, r_by, loc]
        qeue.append(appendable)
    
        await callsmusic.set_stream(chat_id, file_path)
        await cb.message.delete()
        await b.send_photo(chat_id,
            photo="final.png",
            reply_markup=keyboard,
            caption=f"▶️ <b>Oxunur</b> {r_by.mention} tərəfindən Youtube Music ilə qoşuldu 😎",
        )
        os.remove("final.png")