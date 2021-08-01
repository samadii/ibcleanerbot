import os
import logging
import i18n
import json

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    run_async,
    Filters,
    CallbackQueryHandler,
    PollAnswerHandler,
    PollHandler,
)
from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Poll, ParseMode
from telegram.utils.helpers import mention_html
from database import mod_or_make_chat, get_chat


i18n.load_path.append("locale")
i18n.set("filename_format", "{locale}.{format}")
i18n.set("skip_locale_root_data", True)
i18n.set("fallback", "en")


def localize(func):
    def inner(*args, **kwargs):
        locale = ""
        chat_data = get_chat(args[1].effective_chat.id)
        if chat_data:
            locale = chat_data.locale or ""
        i18n.set("locale", locale)
        return func(*args, **kwargs)

    return inner


def admin_only(func):
    def inner(*args, **kwargs):
        original_member = args[2].bot.get_chat_member(
            args[1].effective_chat.id, args[1].effective_user.id
        )
        if original_member["status"] not in ("creator", "administrator"):
            args[2].bot.answer_callback_query(
                callback_query_id=args[1].callback_query.id,
                text=i18n.t("not_permitted"),
            )
            return
        return func(*args, **kwargs)

    return inner


class ibCleanerBot:
    def __init__(self, config):
        self.DEFAULT_VOTE_COUNT = int(config.DEFAULT_VOTE_COUNT)
        self.DEFAULT_DELETE_TIMEOUT = int(config.DEFAULT_DELETE_TIMEOUT)
        self.TOKEN = config.bot_api

    def initialize_bot(self, is_env):
        updater = Updater(token=self.TOKEN, use_context=True)
        dispatcher = updater.dispatcher
        self.foo = dispatcher
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
        )
        start_handler = CommandHandler("start", self.start)
        dispatcher.add_handler(start_handler)
        askdelete_handler = MessageHandler(
            Filters.regex("^@" + updater.bot.username + "$"), self.askdelete
        )
        askdelete_ban_handler = MessageHandler(
            Filters.regex("^@" + updater.bot.username + " ban$"), self.askdelete_ban
        )
        set_handler = CommandHandler("settings", self.set_cmd)
        dispatcher.add_handler(askdelete_handler)
        dispatcher.add_handler(askdelete_ban_handler)
        dispatcher.add_handler(PollAnswerHandler(self.receive_poll_answer))
        dispatcher.add_handler(PollHandler(self.delete))
        dispatcher.add_handler(set_handler)
        dispatcher.add_handler(CallbackQueryHandler(self.query_func))

        if is_env:
            updater.start_polling()
        else:
            updater.start_polling()

    @localize
    def send_locale(self, update, context):
        keyboard = []
        count = 0
        temp = []
        files = os.listdir("locale")
        for _file in files:
            count += 1
            with open(os.path.join("locale", _file), "r") as f:
                data = json.load(f)
                temp.append(
                    InlineKeyboardButton(
                        f'{data["lang_info"]["name"]} {data["lang_info"]["icon"]}',
                        callback_data="locale " + data["lang_info"]["short"],
                    )
                )
            if count % 3 == 0:
                keyboard.append(temp)
                temp = []
            elif count == len(files):
                keyboard.append(temp)
        keyboard.append([InlineKeyboardButton(i18n.t("back"), callback_data="back")])
        update.effective_message.edit_text(
            text=i18n.t("locale_menu"), reply_markup=InlineKeyboardMarkup(keyboard)
        )

    @localize
    def set_option(self, update, context, name, value):
        try:
            value_int = int(value)
        except ValueError:
            value_int = False
        kwargs = {
            "locale": {"locale": value},
            "votes": {"vote_count": value_int},
            "delete_timeout": {"delete_timeout": value_int},
        }[name]
        res = mod_or_make_chat(update.effective_chat.id, **kwargs)
        context.bot.answer_callback_query(
            callback_query_id=update.callback_query.id,
            text=i18n.t(res),
            show_alert=True,
        )
        update.effective_message.delete()

    @localize
    def send_vote_count(self, update, context):
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(x, callback_data="votes " + str(x))
                    for x in [1, 2, 3, 5, 10]
                ],
                [InlineKeyboardButton(i18n.t("back"), callback_data="back")],
            ]
        )
        update.effective_message.edit_text(
            text=i18n.t("vote_menu"), reply_markup=keyboard
        )

    @localize
    def send_delete_timeout(self, update, context):
        second = i18n.t("second")
        minute = i18n.t("minute")
        times = {
            f"5 {second}": "5",
            f"10 {second}": "10",
            f"30 {second}": "30",
            f"1 {minute}": "60",
            f"2 {minute}": "120",
            f"5 {minute}": "300",
            f"10 {minute}": "600",
            f"30 {minute}": "1800",
            i18n.t("immediate"): "-1",
            i18n.t("disable"): "-2",
        }
        keyboard = [
            [InlineKeyboardButton(x, callback_data="delete_timeout " + times[x])]
            for x in times
        ]
        keyboard.append([InlineKeyboardButton(i18n.t("back"), callback_data="back")])
        update.effective_message.edit_text(
            text=i18n.t("timeout_menu"), reply_markup=InlineKeyboardMarkup(keyboard)
        )

    @localize
    @admin_only
    def query_func(self, update, context):
        data = update.callback_query.data
        if data == "language":
            self.send_locale(update, context)
        elif data == "vote_count":
            self.send_vote_count(update, context)
        elif data == "delete_timeout":
            self.send_delete_timeout(update, context)
        elif data == "close":
            update.effective_message.delete()
        elif data == "back":
            update.effective_message.edit_text(**self.gen_set(update, context))
        else:
            args = data.split(" ")
            self.set_option(update, context, args[0], args[1])

    @localize
    def gen_set(self, update, context):
        vote = self.DEFAULT_VOTE_COUNT
        timeout = self.DEFAULT_DELETE_TIMEOUT
        chat_data = get_chat(update.effective_chat.id)
        if chat_data:
            if chat_data.vote_count:
                vote = chat_data.vote_count
            if chat_data.delete_timeout:
                timeout = chat_data.delete_timeout
        time_suffix = i18n.t("second")
        if timeout > 60:
            timeout /= timeout
            time_suffix = i18n.t("minute")
        desc = f'⚙️\n{i18n.t("vote_count")}: {vote}\n{i18n.t("delete_timeout")}: {timeout} {time_suffix}\n\n{i18n.t("main_menu")}'
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(i18n.t("language"), callback_data="language")],
                [
                    InlineKeyboardButton(
                        i18n.t("vote_count"), callback_data="vote_count"
                    )
                ],
                [
                    InlineKeyboardButton(
                        i18n.t("delete_timeout"), callback_data="delete_timeout"
                    )
                ],
                [InlineKeyboardButton("❌", callback_data="close")],
            ]
        )
        return {"text": desc, "reply_markup": keyboard}

    @run_async
    @admin_only
    def set_cmd(self, update, context):
        context.bot.send_message(
            update.effective_chat.id, **self.gen_set(update, context)
        )
        update.effective_message.delete()

    @run_async
    @localize
    def start(self, update, context):
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=i18n.t(
                "bot_welcome",
                name=context.bot.first_name,
                username=context.bot.username,
            ),
        )

    @run_async
    def askdelete(self, update, context):
        self.ask_func(update, context)

    @run_async
    def askdelete_ban(self, update, context):
        self.ask_func(update, context, ban=True)

    @localize
    def ask_func(self, update, context, ban=False):
        if not update.message.reply_to_message:
            return
        update.message.delete()

        del_msg_id = update.message.reply_to_message.message_id
        del_msg_name = update.message.reply_to_message.from_user.first_name
        original_member = context.bot.get_chat_member(
            update.effective_chat.id, update.message.reply_to_message.from_user.id
        )
        if original_member["status"] in ("creator", "administrator"):
            return

        question_string = i18n.t("question_string", name=del_msg_name)
        if ban:
            question_string = i18n.t("question_string_ban", name=del_msg_name)

        questions = [i18n.t("yes"), i18n.t("no")]

        message = context.bot.sendPoll(
            update.effective_chat.id,
            question_string,
            questions,
            is_anonymous=False,
            type="regular",
            allows_multiple_answers=False,
            reply_to_message_id=del_msg_id,
        )

        context.bot_data[message.poll.id] = {}
        context.bot_data[message.poll.id]["count"] = {"yes": 0, "no": 0}
        context.bot_data[message.poll.id]["msg_to_delete"] = del_msg_id
        context.bot_data[message.poll.id]["chat"] = update.effective_chat.id
        context.bot_data[message.poll.id]["message_id"] = message.message_id
        context.bot_data[message.poll.id]["sender_id"] = original_member.user.id
        context.bot_data[message.poll.id]["ban"] = ban
        context.bot_data[message.poll.id]["voters"] = {}

    def sched_delete(self, context):
        job_ctx = context.job.context
        context.bot.delete_message(job_ctx[0], job_ctx[1])

    @run_async
    def receive_poll_answer(self, update, context):
        """Summarize a users poll vote"""
        answer = update.poll_answer
        poll_id = answer.poll_id
        selected_options = answer.option_ids

        timeout = self.DEFAULT_DELETE_TIMEOUT
        vote_count = self.DEFAULT_VOTE_COUNT
        chat_data = get_chat(context.bot_data[poll_id]["chat"])
        if chat_data:
            timeout = chat_data.delete_timeout or self.DEFAULT_DELETE_TIMEOUT
            vote_count = chat_data.vote_count or self.DEFAULT_VOTE_COUNT

        if len(selected_options) < 1:
            context.bot_data[poll_id]["count"][
                context.bot_data[poll_id]["voters"][update.effective_user.id]
            ] -= 1
            return

        if selected_options[0] == 0:
            context.bot_data[poll_id]["count"]["yes"] += 1
            context.bot_data[poll_id]["voters"][update.effective_user.id] = "yes"
        elif selected_options[0] == 1:
            context.bot_data[poll_id]["count"]["no"] += 1
            context.bot_data[poll_id]["voters"][update.effective_user.id] = "no"

        # Close poll after three participants voted
        if (
            context.bot_data[poll_id]["count"]["yes"] == vote_count
            or context.bot_data[poll_id]["count"]["no"] == vote_count
        ):
            context.bot.stop_poll(
                context.bot_data[poll_id]["chat"],
                context.bot_data[poll_id]["message_id"],
            )
            if timeout == -2:
                return
            context.job_queue.run_once(
                self.sched_delete,
                timeout,
                context=(
                    context.bot_data[poll_id]["chat"],
                    context.bot_data[poll_id]["message_id"],
                ),
            )

    @run_async
    def delete(self, update, context):
        vote_count = self.DEFAULT_VOTE_COUNT
        chat_data = get_chat(context.bot_data[update.poll.id]["chat"])
        if chat_data:
            vote_count = chat_data.vote_count or self.DEFAULT_VOTE_COUNT

        if update.poll.options[0].voter_count == vote_count:
            context.bot.delete_message(
                chat_id=context.bot_data[update.poll.id]["chat"],
                message_id=context.bot_data[update.poll.id]["msg_to_delete"],
            )
            if context.bot_data[update.poll.id]["ban"]:
                context.bot.kick_chat_member(
                    chat_id=context.bot_data[update.poll.id]["chat"],
                    user_id=context.bot_data[update.poll.id]["sender_id"],
                )
        if update.poll.is_closed:
            print("test closed")
            return


if __name__ == "__main__":
    IS_ENV = "TRUE"
    if IS_ENV:
        from config import Config
    ibcBot = ibCleanerBot(Config)
    ibcBot.initialize_bot(IS_ENV)
