# -*- coding: utf-8 -*-
import sys

module = sys.modules[__name__]

def setCell( name, value ):
	module.table[name] = value

def getCell( name ):
	return module.table.get( name )

def initConfig():
	module.table = {}


	setCell("waiting_time", 10)

	setCell("vk_name", "как вас зовут в вк")
	setCell("access_token", "вк токен")
	setCell("v", 5.199)
	setCell("peer_id", id_беседы_в_вк)
	setCell("tg_chat_id", id_беседы_в_тг)

	setCell("session_name", "uploader")
	setCell("api_id", 29537595)
	setCell("api_hash", "8826edcd42d52a12c2f077f360ec7b12")

	setCell("project_directory_path", 'путь-до-папки/Vk-to-telegram-transfer-bot/')
	setCell("download_directory_path", 'путь-до-папки/Vk-to-telegram-transfer-bot/Downloads/')

	setCell("vk_group_name", False)     # выводить ли имя группы при пересылке сообщений
	setCell("vk_wall_caption", False)   # выводить ли текст из записи группы при пересылке сообщений

	setCell("bot_name", "имя_вашего_бота")
	setCell( "telegram_token", "токен_вашего_бота" ) # Токен бота в Telegram